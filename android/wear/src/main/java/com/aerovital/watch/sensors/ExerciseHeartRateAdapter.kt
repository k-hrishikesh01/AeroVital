package com.aerovital.watch.sensors

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.util.Log
import androidx.core.content.ContextCompat
import androidx.health.services.client.ExerciseClient
import androidx.health.services.client.ExerciseUpdateCallback
import androidx.health.services.client.HealthServices
import androidx.health.services.client.data.Availability
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DataTypeAvailability
import androidx.health.services.client.data.ExerciseConfig
import androidx.health.services.client.data.ExerciseState
import androidx.health.services.client.data.ExerciseType
import androidx.health.services.client.data.ExerciseUpdate
import androidx.health.services.client.data.SampleDataPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

interface ExerciseProvider {
    fun hasPermission(permission: String): Boolean
    fun isExerciseSupported(): Boolean
    fun startExercise(callback: ExerciseUpdateCallback): Boolean
    fun stopExercise(callback: ExerciseUpdateCallback)
}

class DefaultExerciseProvider(
    private val context: Context,
    private val exerciseClient: ExerciseClient = HealthServices.getClient(context).exerciseClient
) : ExerciseProvider {

    override fun hasPermission(permission: String): Boolean {
        return ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
    }

    override fun isExerciseSupported(): Boolean {
        return try {
            val capabilities = exerciseClient.getCapabilitiesAsync().get()
            capabilities.supportedExerciseTypes.contains(ExerciseType.UNKNOWN) ||
                capabilities.supportedExerciseTypes.isNotEmpty()
        } catch (e: Exception) {
            Log.w(TAG, "Failed to query ExerciseCapabilities: ${e.message}")
            false
        }
    }

    override fun startExercise(callback: ExerciseUpdateCallback): Boolean {
        return try {
            exerciseClient.setUpdateCallback(callback)
            val config = ExerciseConfig.builder(ExerciseType.UNKNOWN)
                .setDataTypes(setOf(DataType.HEART_RATE_BPM))
                .setIsAutoPauseAndResumeEnabled(false)
                .setIsGpsEnabled(false)
                .build()
            exerciseClient.startExerciseAsync(config)
            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start HealthServices ExerciseClient: ${e.message}", e)
            false
        }
    }

    override fun stopExercise(callback: ExerciseUpdateCallback) {
        try {
            exerciseClient.endExerciseAsync()
            exerciseClient.clearUpdateCallbackAsync(callback)
        } catch (e: Exception) {
            Log.w(TAG, "Failed to stop HealthServices ExerciseClient: ${e.message}")
        }
    }

    companion object {
        private const val TAG = "DefaultExerciseProvider"
    }
}

/**
 * SensorAdapter implementing continuous long-running heart-rate acquisition
 * via Health Services ExerciseClient.
 *
 * If ExerciseClient is unsupported on the hardware, unavailable, or superseded by another app,
 * it falls back cleanly to [fallbackAdapter] (MeasureClient).
 */
class ExerciseHeartRateAdapter(
    private val exerciseProvider: ExerciseProvider,
    private val fallbackAdapter: SensorAdapter? = null
) : SensorAdapter {

    override val sensorType: SensorType = SensorType.HEART_RATE

    private var listener: SensorListener? = null
    private var isRegistered: Boolean = false
    private var isUsingFallback: Boolean = false

    private val exerciseCallback = object : ExerciseUpdateCallback {
        override fun onExerciseUpdateReceived(update: ExerciseUpdate) {
            val hrPoints: List<SampleDataPoint<Double>> = update.latestMetrics.getData(DataType.HEART_RATE_BPM)
            for (dp in hrPoints) {
                val bpm = dp.value.toFloat()
                val timestampNs = dp.timeDurationFromBoot.toNanos()
                emitObservation(bpm, timestampNs)
            }

            if (update.exerciseStateInfo.state == ExerciseState.ENDED) {
                val reason = update.exerciseStateInfo.endReason
                Log.w(TAG, "Health Services Exercise session ended: $reason")
                listener?.onAvailabilityChanged(sensorType, SensorAvailability.UNAVAILABLE)
            }
        }

        override fun onLapSummaryReceived(lapSummary: androidx.health.services.client.data.ExerciseLapSummary) {}

        override fun onAvailabilityChanged(dataType: DataType<*, *>, availability: Availability) {
            if (dataType == DataType.HEART_RATE_BPM) {
                val mapped = when (availability) {
                    DataTypeAvailability.AVAILABLE,
                    DataTypeAvailability.ACQUIRING -> SensorAvailability.AVAILABLE
                    else -> SensorAvailability.UNAVAILABLE
                }
                listener?.onAvailabilityChanged(sensorType, mapped)
            }
        }

        override fun onRegistered() {
            Log.i(TAG, "ExerciseUpdateCallback registered successfully")
            listener?.onAvailabilityChanged(sensorType, SensorAvailability.AVAILABLE)
        }

        override fun onRegistrationFailed(throwable: Throwable) {
            Log.e(TAG, "ExerciseUpdateCallback registration failed: ${throwable.message}")
            tryFallback()
        }
    }

    override fun checkAvailability(): SensorAvailability {
        if (!exerciseProvider.hasPermission(Manifest.permission.BODY_SENSORS)) {
            return SensorAvailability.ERROR_NO_PERMISSION
        }
        return if (exerciseProvider.isExerciseSupported()) {
            SensorAvailability.AVAILABLE
        } else {
            fallbackAdapter?.checkAvailability() ?: SensorAvailability.UNAVAILABLE
        }
    }

    override fun start(listener: SensorListener): Boolean {
        if (isRegistered) return true
        this.listener = listener

        if (!exerciseProvider.hasPermission(Manifest.permission.BODY_SENSORS)) {
            listener.onAvailabilityChanged(sensorType, SensorAvailability.ERROR_NO_PERMISSION)
            return false
        }

        val started = exerciseProvider.startExercise(exerciseCallback)
        if (started) {
            isRegistered = true
            isUsingFallback = false
            listener.onAvailabilityChanged(sensorType, SensorAvailability.AVAILABLE)
            return true
        } else {
            Log.w(TAG, "ExerciseClient start returned false, falling back")
            return tryFallback()
        }
    }

    override fun stop() {
        if (isUsingFallback) {
            fallbackAdapter?.stop()
            isUsingFallback = false
        } else if (isRegistered) {
            exerciseProvider.stopExercise(exerciseCallback)
            isRegistered = false
        }
        listener = null
    }

    private fun tryFallback(): Boolean {
        val currentListener = listener ?: return false
        if (fallbackAdapter != null) {
            Log.i(TAG, "Falling back to secondary Heart Rate adapter")
            isUsingFallback = true
            isRegistered = fallbackAdapter.start(currentListener)
            return isRegistered
        }
        currentListener.onAvailabilityChanged(sensorType, SensorAvailability.ERROR_HARDWARE)
        return false
    }

    internal fun emitObservation(bpm: Float, timestampNs: Long) {
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

    internal fun pushUpdateForTest(update: ExerciseUpdate) {
        exerciseCallback.onExerciseUpdateReceived(update)
    }

    internal fun pushAvailabilityForTest(availability: Availability) {
        exerciseCallback.onAvailabilityChanged(DataType.HEART_RATE_BPM, availability)
    }

    companion object {
        private const val TAG = "ExerciseHRAdapter"
    }
}
