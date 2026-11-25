package com.aerovital.phone.data.model.telemetry

import com.google.gson.annotations.SerializedName

/**
 * Data Transfer Object for telemetry samples queried from GET /api/v1/telemetry/.
 */
data class TelemetryDto(
    @SerializedName("id") val id: Long? = null,
    @SerializedName("timestamp") val timestamp: String? = null,
    @SerializedName("heart_rate") val heartRate: Double? = null,
    @SerializedName("spo2") val spo2: Double? = null,
    @SerializedName("skin_temperature") val skinTemperature: Double? = null,
    @SerializedName("activity_level") val activityLevel: String? = null
)
