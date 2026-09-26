package com.aerovital.watch.sensors

import android.Manifest
import android.content.Context
import android.hardware.Sensor

object SensorAdapterFactory {
    
    fun createHeartRateAdapter(context: Context): SensorAdapter {
        return AndroidSensorAdapter(
            sensorProvider = DefaultSensorProvider(context),
            sensorType = SensorType.HEART_RATE,
            androidSensorType = Sensor.TYPE_HEART_RATE,
            unit = "bpm",
            permission = Manifest.permission.BODY_SENSORS
        )
    }

    fun createAccelerometerAdapter(context: Context): SensorAdapter {
        return AndroidSensorAdapter(
            sensorProvider = DefaultSensorProvider(context),
            sensorType = SensorType.ACCELEROMETER,
            androidSensorType = Sensor.TYPE_ACCELEROMETER,
            unit = "m/s^2",
            permission = null // Accelerometer usually does not require runtime permissions
        )
    }

    fun createGyroscopeAdapter(context: Context): SensorAdapter {
        return AndroidSensorAdapter(
            sensorProvider = DefaultSensorProvider(context),
            sensorType = SensorType.GYROSCOPE,
            androidSensorType = Sensor.TYPE_GYROSCOPE,
            unit = "rad/s",
            permission = null
        )
    }
    
    // RR Interval is often implicitly derived or provided through specialized Samsung APIs
    // Using standard SensorManager, it's typically unavailable directly as a raw generic sensor type
    fun createRRIntervalAdapter(): SensorAdapter {
        return UnavailableSensorAdapter(SensorType.RR_INTERVAL)
    }

    fun createSpO2Adapter(): SensorAdapter {
        return UnavailableSensorAdapter(SensorType.SPO2)
    }

    fun createSkinTemperatureAdapter(): SensorAdapter {
        return UnavailableSensorAdapter(SensorType.SKIN_TEMPERATURE)
    }
}
