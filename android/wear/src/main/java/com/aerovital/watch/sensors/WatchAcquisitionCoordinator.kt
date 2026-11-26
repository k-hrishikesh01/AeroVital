package com.aerovital.watch.sensors

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Settings
import android.util.Log
import androidx.core.content.ContextCompat
import com.aerovital.shared.telemetry.CanonicalTelemetry
import com.aerovital.shared.transport.TelemetryAck
import com.aerovital.shared.transport.TelemetryBatch
import com.aerovital.shared.transport.TransportEnvelope
import com.aerovital.shared.transport.TransportResult
import com.aerovital.watch.queue.DurableWatchTelemetryBuffer
import com.aerovital.watch.queue.WatchBatchRecord
import com.aerovital.watch.telemetry.TelemetryMapper
import com.aerovital.watch.telemetry.TelemetryTransportHandoff
import com.aerovital.watch.transport.WatchAckListenerService
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
import java.util.UUID

/**
 * Coordinates physical sensor acquisition on Wear OS with:
 * - 1Hz local sensor aggregation
 * - Bounded 5-10s radio batching for battery efficiency
 * - Durable watch-side storage (observations never cleared before confirmed application ACK)
 * - Chronological ordering, sequence numbers, batch IDs
 * - Bounded exponential backoff on retries during disconnection
 * - Application-level confirmation tracking from phone
 */
class WatchAcquisitionCoordinator(
    private val context: Context,
    val transportSender: WearTransportSender = WearTransportSender(context),
    deviceId: String = resolveDeviceId(context),
    val buffer: DurableWatchTelemetryBuffer = try {
        context.filesDir?.let { DurableWatchTelemetryBuffer.create(context) }
            ?: DurableWatchTelemetryBuffer.createTemporary()
    } catch (e: Throwable) {
        DurableWatchTelemetryBuffer.createTemporary()
    },
    val transportHandoff: TelemetryTransportHandoff = TelemetryTransportHandoff(
        transportSender = transportSender,
        deviceId = deviceId
    ),
    private val coroutineScope: CoroutineScope = CoroutineScope(Dispatchers.Default),
    val heartRateAdapter: SensorAdapter = SensorAdapterFactory.createHeartRateAdapter(context),
    val accelerometerAdapter: SensorAdapter = SensorAdapterFactory.createAccelerometerAdapter(context),
    val gyroscopeAdapter: SensorAdapter = SensorAdapterFactory.createGyroscopeAdapter(context),
    val samplingIntervalMs: Long = 1000L,
    val batchingIntervalMs: Long = if (samplingIntervalMs < 1000L) samplingIntervalMs else 5000L,
    private val mapper: TelemetryMapper = TelemetryMapper()
) {
    val deviceId: String = deviceId

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

    private val _acknowledgedPacketsCount = MutableStateFlow(0L)
    val acknowledgedPacketsCount: StateFlow<Long> = _acknowledgedPacketsCount.asStateFlow()

    private val _lastTransportResult = MutableStateFlow<String?>(null)
    val lastTransportResult: StateFlow<String?> = _lastTransportResult.asStateFlow()

    private val _lastSentMessageId = MutableStateFlow<String?>(null)
    val lastSentMessageId: StateFlow<String?> = _lastSentMessageId.asStateFlow()

    private val _lastAckedMessageId = MutableStateFlow<String?>(null)
    val lastAckedMessageId: StateFlow<String?> = _lastAckedMessageId.asStateFlow()

    private val _pendingBufferCount = MutableStateFlow(buffer.countPending())
    val pendingBufferCount: StateFlow<Int> = _pendingBufferCount.asStateFlow()

    // 1-second sampling buffer & 5-second batching accumulator
    private val observationBuffer = Collections.synchronizedList(mutableListOf<SensorObservation>())
    private val pendingBatchSamples = Collections.synchronizedList(mutableListOf<CanonicalTelemetry>())
    private var sequenceNumber = 0L

    private var samplingJob: Job? = null
    private var transmissionJob: Job? = null

    init {
        refreshNodeStatus()
        refreshAvailabilities()
        WatchAckListenerService.ackHandler = { ack -> onAckReceived(ack) }
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

    fun checkCurrentPermissionState(): SensorPermissionState {
        val state = resolveInitialPermissionState()
        _permissionState.value = state
        return state
    }

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

    fun refreshAvailabilities() {
        _heartRateAvailability.value = heartRateAdapter.checkAvailability()
        _accelerometerAvailability.value = accelerometerAdapter.checkAvailability()
        _gyroscopeAvailability.value = gyroscopeAdapter.checkAvailability()
    }

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
     * Handles application-level confirmation ACK received from the phone.
     * Atomically removes the confirmed batch from durable watch disk storage.
     */
    fun onAckReceived(ack: TelemetryAck) {
        val removed = buffer.markAcknowledged(ack.messageId)
        if (removed) {
            _acknowledgedPacketsCount.update { it + 1 }
            _lastAckedMessageId.value = ack.messageId
            _lastTransportResult.value = "ACK_CONFIRMED (${ack.messageId.take(8)})"
            _pendingBufferCount.value = buffer.countPending()
            Log.d(TAG, "Phone confirmed delivery for batch ${ack.messageId} (status: ${ack.status})")
        }
    }

    /**
     * Starts sensor observation, 1Hz canonical sampling, and periodic batched durable transmission.
     */
    fun startAcquisition() {
        if (_isAcquiring.value) return

        refreshAvailabilities()
        refreshNodeStatus()

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

        heartRateAdapter.start(hrListener)
        accelerometerAdapter.start(accelListener)
        gyroscopeAdapter.start(gyroListener)

        _isAcquiring.value = true

        // 1. Sampling loop (1Hz): generates CanonicalTelemetry from 1-second observation window
        val batchTargetSamples = (batchingIntervalMs / samplingIntervalMs).toInt().coerceAtLeast(1)

        samplingJob = coroutineScope.launch {
            while (isActive) {
                delay(samplingIntervalMs)

                val oneSecondBatch = synchronized(observationBuffer) {
                    val batch = ArrayList(observationBuffer)
                    observationBuffer.clear()
                    batch
                }

                if (oneSecondBatch.isNotEmpty()) {
                    try {
                        val canonical = mapper.map(oneSecondBatch)
                        synchronized(pendingBatchSamples) {
                            pendingBatchSamples.add(canonical)
                            if (pendingBatchSamples.size >= batchTargetSamples) {
                                flushSamplesToDurableBuffer()
                            }
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Error mapping 1s observation batch: ${e.message}", e)
                    }
                }
            }
        }

        // 2. Transmission & Retry worker loop: drains pending batches from durable buffer to phone
        transmissionJob = coroutineScope.launch {
            while (isActive) {
                delay(batchingIntervalMs)
                dispatchPendingBatches()
            }
        }
    }

    /**
     * Flushes currently accumulated 1s canonical samples into a durable TelemetryBatch envelope on disk.
     */
    fun flushSamplesToDurableBuffer() {
        val samplesToFlush = synchronized(pendingBatchSamples) {
            val list = ArrayList(pendingBatchSamples)
            pendingBatchSamples.clear()
            list
        }
        if (samplesToFlush.isEmpty()) return

        val batchId = UUID.randomUUID().toString()
        val seq = ++sequenceNumber
        val batchPayload = TelemetryBatch(
            batchId = batchId,
            samples = samplesToFlush
        )

        val envelope = TransportEnvelope(
            version = TransportEnvelope.CURRENT_VERSION,
            messageId = batchId,
            deviceId = deviceId,
            timestamp = System.currentTimeMillis(),
            payloadType = TransportEnvelope.PAYLOAD_TYPE_TELEMETRY_BATCH,
            payload = batchPayload.toJson(),
            sequenceNumber = seq,
            batchId = batchId
        )

        buffer.enqueue(envelope)
        _pendingBufferCount.value = buffer.countPending()
        Log.d(TAG, "Enqueued batch $batchId (samples: ${samplesToFlush.size}, seq: $seq) durably to disk")
    }

    /**
     * Dispatches pending unacknowledged batches from durable watch storage to the phone.
     */
    suspend fun dispatchPendingBatches() {
        val pending = buffer.peekPending(limit = 10)
        _pendingBufferCount.value = buffer.countPending()
        if (pending.isEmpty()) return

        val connectedNodes = try {
            transportSender.getConnectedNodeIds()
        } catch (e: Exception) {
            emptyList()
        }
        _connectedNodesCount.value = connectedNodes.size

        val isConnected = connectedNodes.isNotEmpty()
        if (!isConnected) {
            _lastTransportResult.value = "DISCONNECTED (${pending.size} buffered)"
            for (record in pending) {
                buffer.markTransmissionFailure(record.messageId, isLinkConnected = false)
            }
            return
        }

        for (record in pending) {
            val envelope = record.toTransportEnvelope()
            if (envelope == null) {
                // Malformed record on disk; evict
                buffer.markAcknowledged(record.messageId)
                continue
            }

            _lastSentMessageId.value = envelope.messageId
            val result = transportSender.sendEnvelope(envelope)
            when (result) {
                is TransportResult.Success -> {
                    _packetsSent.update { it + 1 }
                    _lastTransportResult.value = "SUCCESS (${envelope.messageId.take(8)})"
                    Log.d(TAG, "Transmitted batch ${envelope.messageId} to phone, awaiting durable ACK")
                }
                is TransportResult.Error -> {
                    buffer.markTransmissionFailure(record.messageId, isLinkConnected = true)
                    _lastTransportResult.value = "${result.reason}: ${result.message}"
                    Log.w(TAG, "Transmission failed for batch ${record.messageId}: ${result.reason}")
                }
            }
        }
        _pendingBufferCount.value = buffer.countPending()
    }

    /**
     * Stops sensor observation and cancels transmission workers.
     */
    fun stopAcquisition() {
        samplingJob?.cancel()
        samplingJob = null
        transmissionJob?.cancel()
        transmissionJob = null

        heartRateAdapter.stop()
        accelerometerAdapter.stop()
        gyroscopeAdapter.stop()

        // Flush any remaining samples to durable disk before stopping
        synchronized(pendingBatchSamples) {
            if (pendingBatchSamples.isNotEmpty()) {
                flushSamplesToDurableBuffer()
            }
        }

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
