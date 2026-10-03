package com.aerovital.watch.sensors

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.util.Log
import androidx.core.content.ContextCompat
import androidx.health.services.client.HealthServices
import androidx.health.services.client.MeasureCallback
import androidx.health.services.client.MeasureClient
import androidx.health.services.client.data.Availability
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DataTypeAvailability
import androidx.health.services.client.data.DeltaDataType
import androidx.health.services.client.data.SampleDataPoint

interface HealthMeasureProvider {
    fun hasPermission(permission: String): Boolean
    fun registerMeasureCallback(
        dataType: DeltaDataType<*, *>,
        callback: MeasureCallback
    )
    fun unregisterMeasureCallback(
        dataType: DeltaDataType<*, *>,
        callback: MeasureCallback
    )
}

class DefaultHealthMeasureProvider(
    private val context: Context,
    private val measureClient: MeasureClient = HealthServices.getClient(context).measureClient
) : HealthMeasureProvider {
    override fun hasPermission(permission: String): Boolean {
        return ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
    }

    override fun registerMeasureCallback(
        dataType: DeltaDataType<*, *>,
        callback: MeasureCallback
    ) {
        val executor = ContextCompat.getMainExecutor(context)
        measureClient.registerMeasureCallback(dataType, executor, callback)
    }

    override fun unregisterMeasureCallback(
        dataType: DeltaDataType<*, *>,
        callback: MeasureCallback
    ) {
        measureClient.unregisterMeasureCallbackAsync(dataType, callback)
    }
}

class HealthServicesHeartRateAdapter(
    private val measureProvider: HealthMeasureProvider
) : SensorAdapter {

    override val sensorType: SensorType = SensorType.HEART_RATE

    private var listener: SensorListener? = null
    private var isRegistered: Boolean = false

    private val measureCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            if (dataType == DataType.HEART_RATE_BPM) {
                val sensorAvailability = when (availability) {
                    DataTypeAvailability.AVAILABLE,
                    DataTypeAvailability.ACQUIRING -> SensorAvailability.AVAILABLE
                    DataTypeAvailability.UNAVAILABLE,
                    DataTypeAvailability.UNAVAILABLE_DEVICE_OFF_BODY -> SensorAvailability.UNAVAILABLE
                    else -> SensorAvailability.UNAVAILABLE
                }
                Log.i(TAG, "WHS HeartRate availability changed: $availability -> $sensorAvailability")
                listener?.onAvailabilityChanged(sensorType, sensorAvailability)
            }
        }

        override fun onDataReceived(data: DataPointContainer) {
            val hrDataPoints: List<SampleDataPoint<Double>> = data.getData(DataType.HEART_RATE_BPM)
            for (dp in hrDataPoints) {
                val bpm = dp.value.toFloat()
                val timestampNs = dp.timeDurationFromBoot.toNanos()
                Log.i(TAG, "WHS HeartRate sample received: $bpm bpm at ${timestampNs}ns")
                emitHeartRateObservation(bpm, timestampNs)
            }
        }

        override fun onRegistrationFailed(throwable: Throwable) {
            Log.e(TAG, "HealthServices MeasureCallback registration failed: ${throwable.message}")
            isRegistered = false
            listener?.onAvailabilityChanged(sensorType, SensorAvailability.ERROR_HARDWARE)
        }
    }

    override fun checkAvailability(): SensorAvailability {
        if (!measureProvider.hasPermission(Manifest.permission.BODY_SENSORS)) {
            return SensorAvailability.ERROR_NO_PERMISSION
        }
        return SensorAvailability.AVAILABLE
    }

    override fun start(listener: SensorListener): Boolean {
        if (isRegistered) return true

        val availability = checkAvailability()
        if (availability != SensorAvailability.AVAILABLE) {
            listener.onAvailabilityChanged(sensorType, availability)
            return false
        }

        this.listener = listener
        return try {
            measureProvider.registerMeasureCallback(DataType.HEART_RATE_BPM, measureCallback)
            isRegistered = true
            listener.onAvailabilityChanged(sensorType, SensorAvailability.AVAILABLE)
            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to register HealthServices MeasureCallback: ${e.message}", e)
            isRegistered = false
            listener.onAvailabilityChanged(sensorType, SensorAvailability.ERROR_HARDWARE)
            false
        }
    }

    override fun stop() {
        if (isRegistered) {
            try {
                measureProvider.unregisterMeasureCallback(DataType.HEART_RATE_BPM, measureCallback)
            } catch (e: Exception) {
                Log.w(TAG, "Failed to unregister HealthServices MeasureCallback: ${e.message}")
            }
            isRegistered = false
        }
        listener = null
    }

    internal fun emitHeartRateObservation(bpm: Float, timestampNs: Long) {
        val currentListener = listener ?: return
        val observation = SensorObservation(
            timestampNs = timestampNs,
            sensorType = sensorType,
            values = floatArrayOf(bpm),
            unit = "bpm",
            status = null
        )
        currentListener.onObservation(observation)
    }

    internal fun pushObservationForTest(data: DataPointContainer) {
        measureCallback.onDataReceived(data)
    }

    internal fun pushAvailabilityForTest(availability: Availability) {
        measureCallback.onAvailabilityChanged(DataType.HEART_RATE_BPM, availability)
    }

    internal fun pushRegistrationFailureForTest(throwable: Throwable) {
        measureCallback.onRegistrationFailed(throwable)
    }

    companion object {
        private const val TAG = "HealthServicesHRAdapter"
    }
}
