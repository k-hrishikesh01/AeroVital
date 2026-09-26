package com.aerovital.watch.sensors

enum class SensorType {
    HEART_RATE,
    RR_INTERVAL,
    SPO2,
    SKIN_TEMPERATURE,
    ACCELEROMETER,
    GYROSCOPE,
    STEP_COUNTER
}

enum class SensorAvailability {
    AVAILABLE,
    UNAVAILABLE,
    ERROR_NO_PERMISSION,
    ERROR_HARDWARE
}

enum class SensorPermissionState {
    GRANTED,
    DENIED,
    NOT_YET_REQUESTED
}

data class SensorObservation(
    val timestampNs: Long, // Originating sensor timestamp in nanoseconds where possible
    val sensorType: SensorType,
    val values: FloatArray,
    val unit: String,
    val status: Int? = null // Optional accuracy or hardware status flag
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false

        other as SensorObservation

        if (timestampNs != other.timestampNs) return false
        if (sensorType != other.sensorType) return false
        if (!values.contentEquals(other.values)) return false
        if (unit != other.unit) return false
        if (status != other.status) return false

        return true
    }

    override fun hashCode(): Int {
        var result = timestampNs.hashCode()
        result = 31 * result + sensorType.hashCode()
        result = 31 * result + values.contentHashCode()
        result = 31 * result + unit.hashCode()
        result = 31 * result + (status ?: 0)
        return result
    }
}
