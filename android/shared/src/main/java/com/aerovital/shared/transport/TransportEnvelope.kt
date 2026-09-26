package com.aerovital.shared.transport

import com.google.gson.annotations.SerializedName

data class TransportEnvelope(
    @SerializedName("version") val version: Int,
    @SerializedName("messageId") val messageId: String,
    @SerializedName("deviceId") val deviceId: String,
    @SerializedName("timestamp") val timestamp: Long,
    @SerializedName("payloadType") val payloadType: String,
    @SerializedName("payload") val payload: String,
    @SerializedName("sequenceNumber") val sequenceNumber: Long? = null
) {
    companion object {
        const val CURRENT_VERSION = 1
        
        const val PAYLOAD_TYPE_TEST = "TEST"
        const val PAYLOAD_TYPE_TELEMETRY = "PHYSIOLOGICAL_TELEMETRY" // Reserved for A3/A4
        
        // Envelope validation rules
        fun validate(envelope: TransportEnvelope, currentTimeMillis: Long): TransportResult<TransportEnvelope> {
            if (envelope.version <= 0) {
                return TransportResult.Error(ErrorReason.MALFORMED_ENVELOPE, "Invalid version")
            }
            if (envelope.version > CURRENT_VERSION) {
                return TransportResult.Error(ErrorReason.UNSUPPORTED_VERSION, "Unsupported version")
            }
            if (envelope.messageId.isBlank()) {
                return TransportResult.Error(ErrorReason.MALFORMED_ENVELOPE, "Missing messageId")
            }
            if (envelope.deviceId.isBlank()) {
                return TransportResult.Error(ErrorReason.MALFORMED_ENVELOPE, "Missing deviceId")
            }
            if (envelope.payload.isBlank()) {
                return TransportResult.Error(ErrorReason.MALFORMED_ENVELOPE, "Missing payload")
            }
            
            // Payload type verification
            if (envelope.payloadType != PAYLOAD_TYPE_TEST && envelope.payloadType != PAYLOAD_TYPE_TELEMETRY) {
                return TransportResult.Error(ErrorReason.UNKNOWN_PAYLOAD_TYPE, "Unknown payload type: ${envelope.payloadType}")
            }
            
            // Timestamp validation
            if (envelope.timestamp <= 0) {
                return TransportResult.Error(ErrorReason.MALFORMED_ENVELOPE, "Invalid timestamp")
            }
            
            val age = currentTimeMillis - envelope.timestamp
            
            // Future timestamp handling with bounded clock-skew tolerance (5 seconds)
            if (age < -CLOCK_SKEW_TOLERANCE_MS) {
                return TransportResult.Error(ErrorReason.FUTURE_TIMESTAMP, "Timestamp is too far in the future")
            }
            
            // Stale timestamp handling (1 hour)
            if (age > STALE_THRESHOLD_MS) {
                return TransportResult.Error(ErrorReason.STALE_MESSAGE, "Message is too old")
            }
            
            return TransportResult.Success(envelope)
        }
        
        // 5 seconds tolerance for minor clock drift between devices
        const val CLOCK_SKEW_TOLERANCE_MS = 5000L
        // 1 hour staleness limit
        const val STALE_THRESHOLD_MS = 3600_000L
    }
}
