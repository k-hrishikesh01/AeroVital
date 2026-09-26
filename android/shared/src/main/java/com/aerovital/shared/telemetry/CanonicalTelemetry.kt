package com.aerovital.shared.telemetry

import com.aerovital.shared.transport.TransportEnvelope
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import java.util.UUID

/**
 * Canonical AeroVital Telemetry representation.
 *
 * Corresponds strictly to the backend-facing AeroVital telemetry contract
 * (defined in backend/core/schemas/telemetry.py and django-backend/telemetry/models.py).
 * Non-essential or unobserved channels are optional (nullable) to support
 * diverse wearable sensor capabilities without fabrication, zero-filling, or imputation.
 */
data class CanonicalTelemetry(
    @SerializedName("timestamp") val timestamp: String,
    @SerializedName("heart_rate") val heartRate: Float? = null,
    @SerializedName("rr_interval") val rrInterval: List<Float>? = null,
    @SerializedName("spo2") val spo2: Float? = null,
    @SerializedName("skin_temperature") val skinTemperature: Float? = null,
    @SerializedName("activity_level") val activityLevel: Any? = null,
    @SerializedName("steps") val steps: Int? = null,
    @SerializedName("accel_x") val accelX: Float? = null,
    @SerializedName("accel_y") val accelY: Float? = null,
    @SerializedName("accel_z") val accelZ: Float? = null,
    @SerializedName("battery_level") val batteryLevel: Float? = null,
    @SerializedName("raw_payload") val rawPayload: Map<String, Any>? = null
) {
    /**
     * Checks whether a complete 3-axis accelerometer triplet is present.
     */
    fun hasAcceleration(): Boolean {
        return accelX != null && accelY != null && accelZ != null
    }

    /**
     * Serializes this canonical telemetry into the existing A2 TransportEnvelope.
     */
    fun toTransportEnvelope(
        deviceId: String,
        messageId: String = UUID.randomUUID().toString(),
        timestampEpochMs: Long = System.currentTimeMillis(),
        sequenceNumber: Long? = null,
        gson: Gson = Gson()
    ): TransportEnvelope {
        return TransportEnvelope(
            version = TransportEnvelope.CURRENT_VERSION,
            messageId = messageId,
            deviceId = deviceId,
            timestamp = timestampEpochMs,
            payloadType = TransportEnvelope.PAYLOAD_TYPE_TELEMETRY,
            payload = gson.toJson(this),
            sequenceNumber = sequenceNumber
        )
    }

    companion object {
        /**
         * Parses a CanonicalTelemetry payload from an existing TransportEnvelope.
         * Returns null if payloadType does not match or parsing fails.
         */
        fun fromTransportEnvelope(
            envelope: TransportEnvelope,
            gson: Gson = Gson()
        ): CanonicalTelemetry? {
            if (envelope.payloadType != TransportEnvelope.PAYLOAD_TYPE_TELEMETRY) {
                return null
            }
            return try {
                gson.fromJson(envelope.payload, CanonicalTelemetry::class.java)
            } catch (e: Exception) {
                null
            }
        }
    }
}

/**
 * Extension helper to parse CanonicalTelemetry directly from a TransportEnvelope.
 */
fun TransportEnvelope.toCanonicalTelemetry(gson: Gson = Gson()): CanonicalTelemetry? {
    return CanonicalTelemetry.fromTransportEnvelope(this, gson)
}
