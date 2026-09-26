package com.aerovital.watch.sensors

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Settings
import android.util.Log
import androidx.core.content.ContextCompat
import com.aerovital.shared.transport.TransportEnvelope
import com.aerovital.shared.transport.TransportResult
import com.aerovital.watch.telemetry.TelemetryTransportHandoff
import com.aerovital.watch.transport.WearTransportSender
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.util.Collections

/**
 * Coordinates physical sensor acquisition on Wear OS and dispatches 1Hz batched
 * canonical telemetry envelopes to the phone via the existing A2/A3/A4 pipeline.
 *
 * Responsibilities:
 * - Runtime BODY_SENSORS permission state tracking and enforcement
 * - Sensor lifecycle (Heart Rate, Accelerometer, Gyroscope)
 * - Observation aggregation over 1-second sampling windows
 * - Handoff to TelemetryTransportHandoff and WearTransportSender
 * - Observable diagnostic state for the watch diagnostic surface
 */
class WatchAcquisitionCoordinator(
    private val context: Context,
    val transportSender: WearTransportSender = WearTransportSender(context),
    deviceId: String = resolveDeviceId(context),
    val transportHandoff: TelemetryTransportHandoff = TelemetryTransportHandoff(
        transportSender = transportSender,
        deviceId = deviceId
    ),
    private val coroutineScope: CoroutineScope = CoroutineScope(Dispatchers.Default),
    val heartRateAdapter: SensorAdapter = SensorAdapterFactory.createHeartRateAdapter(context),
    val accelerometerAdapter: SensorAdapter = SensorAdapterFactory.createAccelerometerAdapter(context),
    val gyroscopeAdapter: SensorAdapter = SensorAdapterFactory.createGyroscopeAdapter(context),
    private val samplingIntervalMs: Long = 1000L
) {
    // Observable UI State
    private val _permissionState = MutableStateFlow(resolveInitialPermissionState())
    val permissionState: StateFlow<SensorPermissionState> = _permissionState.asStateFlow()

    private val _heartRateAvailability = MutableStateFlow(heartRateAdapter.checkAvailability())
    val heartRateAvailability: StateFlow<SensorAvailability> = _heartRateAvailability.asStateFlow()

    private val _accelerometerAvailability = MutableStateFlow(accelerometerAdapter.checkAvailability())
    val accelerometerAvailability: StateFlow<SensorAvailability> = _accelerometerAvailability.asStateFlow()

    private val _gyroscopeAvailability = MutableStateFlow(gyroscopeAdapter.checkAvailability())
    val gyroscopeAvailability: StateFlow<SensorAvailability> = _gyroscopeAvailability.asStateFlow()

    private val _latestHeartRate = MutableStateFlow<Float?>(null)
    val latestHeartRate: StateFlow<Float?> = _latestHeartRate.asStateFlow()

    private val _latestAccel = MutableStateFlow<FloatArray?>(null)
    val latestAccel: StateFlow<FloatArray?> = _latestAccel.asStateFlow()

    private val _latestGyro = MutableStateFlow<FloatArray?>(null)
    val latestGyro: StateFlow<FloatArray?> = _latestGyro.asStateFlow()

    private val _isAcquiring = MutableStateFlow(false)
    val isAcquiring: StateFlow<Boolean> = _isAcquiring.asStateFlow()

    private val _connectedNodesCount = MutableStateFlow(0)
    val connectedNodesCount: StateFlow<Int> = _connectedNodesCount.asStateFlow()

    private val _packetsSent = MutableStateFlow(0L)
    val packetsSent: StateFlow<Long> = _packetsSent.asStateFlow()

    private val _lastTransportResult = MutableStateFlow<String?>(null)
    val lastTransportResult: StateFlow<String?> = _lastTransportResult.asStateFlow()

    private val _lastSentMessageId = MutableStateFlow<String?>(null)
    val lastSentMessageId: StateFlow<String?> = _lastSentMessageId.asStateFlow()

    // 1-second batching buffer
    private val observationBuffer = Collections.synchronizedList(mutableListOf<SensorObservation>())
    private var tickerJob: Job? = null

    init {
        refreshNodeStatus()
        refreshAvailabilities()
    }

    private fun resolveInitialPermissionState(): SensorPermissionState {
        val hasPerm = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.BODY_SENSORS
        ) == PackageManager.PERMISSION_GRANTED

        return if (hasPerm) {
            SensorPermissionState.GRANTED
        } else {
            val requested = context
                .getSharedPreferences(PREFS_PERMISSIONS, Context.MODE_PRIVATE)
                .getBoolean(Manifest.permission.BODY_SENSORS, false)
            if (requested) SensorPermissionState.DENIED else SensorPermissionState.NOT_YET_REQUESTED
        }
    }

    /**
     * Checks and updates current permission state.
     */
    fun checkCurrentPermissionState(): SensorPermissionState {
        val state = resolveInitialPermissionState()
        _permissionState.value = state
        return state
    }

    /**
     * Called when the runtime permission request dialog completes.
     */
    fun onPermissionResult(granted: Boolean) {
        context.getSharedPreferences(PREFS_PERMISSIONS, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(Manifest.permission.BODY_SENSORS, true)
            .apply()

        _permissionState.value = if (granted) {
            SensorPermissionState.GRANTED
        } else {
            SensorPermissionState.DENIED
        }

        refreshAvailabilities()
    }

    /**
     * Re-checks sensor hardware availability flags.
     */
    fun refreshAvailabilities() {
        _heartRateAvailability.value = heartRateAdapter.checkAvailability()
        _accelerometerAvailability.value = accelerometerAdapter.checkAvailability()
        _gyroscopeAvailability.value = gyroscopeAdapter.checkAvailability()
    }

    /**
     * Checks connected phone nodes via transport sender.
     */
    fun refreshNodeStatus() {
        coroutineScope.launch {
            try {
                val nodes = transportSender.getConnectedNodeIds()
                _connectedNodesCount.value = nodes.size
            } catch (e: Exception) {
                Log.w(TAG, "Failed to query connected phone nodes: ${e.message}")
            }
        }
    }

    /**
     * Starts sensor observation and periodic 1Hz transmission window.
     */
    fun startAcquisition() {
        if (_isAcquiring.value) return

        refreshAvailabilities()
        refreshNodeStatus()

        // Sensor listeners
        val hrListener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {
                if (observation.values.isNotEmpty()) {
                    _latestHeartRate.value = observation.values[0]
                }
                observationBuffer.add(observation)
            }

            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {
                _heartRateAvailability.value = availability
            }
        }

        val accelListener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {
                _latestAccel.value = observation.values.clone()
                observationBuffer.add(observation)
            }

            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {
                _accelerometerAvailability.value = availability
            }
        }

        val gyroListener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {
                _latestGyro.value = observation.values.clone()
                observationBuffer.add(observation)
            }

            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {
                _gyroscopeAvailability.value = availability
            }
        }

        // Start available sensors
        heartRateAdapter.start(hrListener)
        accelerometerAdapter.start(accelListener)
        gyroscopeAdapter.start(gyroListener)

        _isAcquiring.value = true

        // 1-second transmission ticker
        tickerJob = coroutineScope.launch {
            while (isActive) {
                delay(samplingIntervalMs)

                val currentBatch = synchronized(observationBuffer) {
                    val batch = ArrayList(observationBuffer)
                    observationBuffer.clear()
                    batch
                }

                if (currentBatch.isNotEmpty()) {
                    try {
                        val envelope: TransportEnvelope = transportHandoff.prepareEnvelope(currentBatch)
                        _lastSentMessageId.value = envelope.messageId

                        val sendResult = transportSender.sendEnvelope(envelope)
                        when (sendResult) {
                            is TransportResult.Success -> {
                                _packetsSent.update { it + 1 }
                                _lastTransportResult.value = "SUCCESS (${envelope.messageId.take(8)})"
                                Log.d(TAG, "Sent envelope ${envelope.messageId} (observations: ${currentBatch.size})")
                            }
                            is TransportResult.Error -> {
                                _lastTransportResult.value = "${sendResult.reason}: ${sendResult.message}"
                                Log.w(TAG, "Transport send failed: ${sendResult.reason} - ${sendResult.message}")
                            }
                        }
                    } catch (e: Exception) {
                        _lastTransportResult.value = "EXCEPTION: ${e.message}"
                        Log.e(TAG, "Exception during telemetry transmission: ${e.message}", e)
                    }
                }
            }
        }
    }

    /**
     * Stops sensor observation and cancels periodic transmission.
     */
    fun stopAcquisition() {
        tickerJob?.cancel()
        tickerJob = null

        heartRateAdapter.stop()
        accelerometerAdapter.stop()
        gyroscopeAdapter.stop()

        synchronized(observationBuffer) {
            observationBuffer.clear()
        }

        _isAcquiring.value = false
        Log.d(TAG, "Stopped sensor acquisition")
    }

    companion object {
        private const val TAG = "WatchAcquisitionCoord"
        private const val PREFS_PERMISSIONS = "aerovital_sensor_permissions"

        fun resolveDeviceId(context: Context): String {
            val androidId = try {
                Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
            } catch (e: Exception) {
                null
            }
            return if (!androidId.isNullOrBlank()) {
                "wear-$androidId"
            } else {
                "wear-${Build.MODEL.replace(" ", "-")}"
            }
        }
    }
}
