package com.aerovital.watch.sensors

interface SensorListener {
    fun onObservation(observation: SensorObservation)
    fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability)
}

interface SensorAdapter {
    val sensorType: SensorType
    fun checkAvailability(): SensorAvailability
    fun start(listener: SensorListener): Boolean
    fun stop()
}
