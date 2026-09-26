package com.aerovital.watch.sensors

import android.content.Context
import android.content.pm.PackageManager
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import androidx.core.content.ContextCompat

interface SensorProvider {
    fun hasPermission(permission: String): Boolean
    fun permissionState(permission: String): SensorPermissionState
    fun hasSensor(type: Int): Boolean
    fun registerListener(listener: SensorEventListener, type: Int): Boolean
    fun unregisterListener(listener: SensorEventListener)
}

class DefaultSensorProvider(private val context: Context) : SensorProvider {
    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager

    override fun hasPermission(permission: String): Boolean {
        return ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
    }

    override fun permissionState(permission: String): SensorPermissionState {
        if (hasPermission(permission)) {
            return SensorPermissionState.GRANTED
        }

        val requested = context
            .getSharedPreferences("aerovital_sensor_permissions", Context.MODE_PRIVATE)
            .getBoolean(permission, false)

        return if (requested) {
            SensorPermissionState.DENIED
        } else {
            SensorPermissionState.NOT_YET_REQUESTED
        }
    }

    fun markPermissionRequestAttempted(permission: String) {
        context
            .getSharedPreferences("aerovital_sensor_permissions", Context.MODE_PRIVATE)
            .edit()
            .putBoolean(permission, true)
            .apply()
    }

    override fun hasSensor(type: Int): Boolean {
        return sensorManager.getDefaultSensor(type) != null
    }

    override fun registerListener(listener: SensorEventListener, type: Int): Boolean {
        val sensor = sensorManager.getDefaultSensor(type) ?: return false
        return sensorManager.registerListener(listener, sensor, SensorManager.SENSOR_DELAY_NORMAL)
    }

    override fun unregisterListener(listener: SensorEventListener) {
        sensorManager.unregisterListener(listener)
    }
}

class AndroidSensorAdapter(
    private val sensorProvider: SensorProvider,
    override val sensorType: SensorType,
    private val androidSensorType: Int,
    private val unit: String,
    private val permission: String? = null
) : SensorAdapter, SensorEventListener {

    private var listener: SensorListener? = null
    private var isRegistered = false

    override fun checkAvailability(): SensorAvailability {
        if (permission != null && !sensorProvider.hasPermission(permission)) {
            return SensorAvailability.ERROR_NO_PERMISSION
        }
        return if (sensorProvider.hasSensor(androidSensorType)) {
            SensorAvailability.AVAILABLE
        } else {
            SensorAvailability.UNAVAILABLE
        }
    }

    override fun start(listener: SensorListener): Boolean {
        if (isRegistered) return true // Already started

        val availability = checkAvailability()
        if (availability != SensorAvailability.AVAILABLE) {
            listener.onAvailabilityChanged(sensorType, availability)
            return false
        }

        this.listener = listener
        isRegistered = sensorProvider.registerListener(this, androidSensorType)
        
        if (isRegistered) {
            listener.onAvailabilityChanged(sensorType, SensorAvailability.AVAILABLE)
        } else {
            listener.onAvailabilityChanged(sensorType, SensorAvailability.ERROR_HARDWARE)
        }
        
        return isRegistered
    }

    override fun stop() {
        if (isRegistered) {
            sensorProvider.unregisterListener(this)
            isRegistered = false
        }
        listener = null
    }

    override fun onSensorChanged(event: SensorEvent?) {
        event ?: return
        val currentListener = listener ?: return

        // SensorEvent.timestamp is in nanoseconds since device boot
        val observation = SensorObservation(
            timestampNs = event.timestamp,
            sensorType = sensorType,
            values = event.values.clone(),
            unit = unit,
            status = event.accuracy
        )
        currentListener.onObservation(observation)
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        // Not implemented explicitly to push, handled in values if needed.
    }
    
    // Extracted for testing without SensorEvent reflection issues
    fun pushMockObservation(timestampNs: Long, values: FloatArray, accuracy: Int) {
        listener?.onObservation(
            SensorObservation(
                timestampNs = timestampNs,
                sensorType = sensorType,
                values = values,
                unit = unit,
                status = accuracy
            )
        )
    }
}
