package com.aerovital.watch.sensors

class UnavailableSensorAdapter(
    override val sensorType: SensorType
) : SensorAdapter {

    override fun checkAvailability(): SensorAvailability {
        return SensorAvailability.UNAVAILABLE
    }

    override fun start(listener: SensorListener): Boolean {
        listener.onAvailabilityChanged(sensorType, SensorAvailability.UNAVAILABLE)
        return false
    }

    override fun stop() {
        // No-op
    }
}
