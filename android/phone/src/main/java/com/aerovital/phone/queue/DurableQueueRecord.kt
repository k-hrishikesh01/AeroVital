package com.aerovital.phone.queue

import com.aerovital.shared.telemetry.CanonicalTelemetry
import com.aerovital.shared.telemetry.toCanonicalTelemetry
import com.aerovital.shared.transport.TransportEnvelope
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName

/**
 * Persisted record stored within the phone's durable store-and-forward queue.
 *
 * Preserves the exact identity and envelope fields from the A2 TransportEnvelope:
 * - messageId: Primary identity (never duplicated or regenerated)
 * - deviceId, timestamp, sequenceNumber, payloadType, payload, version
 *
 * In addition, tracks queue management metadata:
 * - enqueueTimeEpochMs: Arrival timestamp in the queue
 * - attemptCount: Number of HTTP transmission attempts
 * - deliveryState: Current lifecycle state
 * - lastFailureClassification: Categorization of the most recent error
 * - lastFailureMessage: Sanitized error description
 * - lastAttemptEpochMs: Timestamp of the most recent transmission attempt
 * - nextRetryEpochMs: Earliest epoch ms when retry is eligible under backoff policy
 */
data class DurableQueueRecord(
    @SerializedName("message_id") val messageId: String,
    @SerializedName("device_id") val deviceId: String,
    @SerializedName("timestamp") val timestamp: Long,
    @SerializedName("sequence_number") val sequenceNumber: Long? = null,
    @SerializedName("payload_type") val payloadType: String,
    @SerializedName("payload") val payload: String,
    @SerializedName("version") val version: Int = TransportEnvelope.CURRENT_VERSION,
    @SerializedName("enqueue_time_ms") val enqueueTimeEpochMs: Long = System.currentTimeMillis(),
    @SerializedName("attempt_count") var attemptCount: Int = 0,
    @SerializedName("delivery_state") var deliveryState: DeliveryState = DeliveryState.PENDING,
    @SerializedName("last_failure_classification") var lastFailureClassification: String? = null,
    @SerializedName("last_failure_message") var lastFailureMessage: String? = null,
    @SerializedName("last_attempt_ms") var lastAttemptEpochMs: Long? = null,
    @SerializedName("next_retry_ms") var nextRetryEpochMs: Long? = null
) {
    /**
     * Reconstructs the exact existing A2 TransportEnvelope without modifying its contract.
     */
    fun toTransportEnvelope(): TransportEnvelope {
        return TransportEnvelope(
            version = version,
            messageId = messageId,
            deviceId = deviceId,
            timestamp = timestamp,
            payloadType = payloadType,
            payload = payload,
            sequenceNumber = sequenceNumber
        )
    }

    /**
     * Extracts the canonical telemetry payload from the persisted envelope data.
     */
    fun toCanonicalTelemetry(gson: Gson = Gson()): CanonicalTelemetry? {
        return toTransportEnvelope().toCanonicalTelemetry(gson)
    }

    companion object {
        /**
         * Reconstructs a DurableQueueRecord from a received TransportEnvelope.
         */
        fun fromTransportEnvelope(
            envelope: TransportEnvelope,
            enqueueTimeEpochMs: Long = System.currentTimeMillis()
        ): DurableQueueRecord {
            return DurableQueueRecord(
                messageId = envelope.messageId,
                deviceId = envelope.deviceId,
                timestamp = envelope.timestamp,
                sequenceNumber = envelope.sequenceNumber,
                payloadType = envelope.payloadType,
                payload = envelope.payload,
                version = envelope.version,
                enqueueTimeEpochMs = enqueueTimeEpochMs,
                attemptCount = 0,
                deliveryState = DeliveryState.PENDING,
                lastFailureClassification = null,
                lastFailureMessage = null,
                lastAttemptEpochMs = null,
                nextRetryEpochMs = null
            )
        }

        /**
         * Deterministic queue ordering rule:
         * 1. Primary: Originating observation timestamp ascending (chronological replay)
         * 2. Secondary: Sequence number ascending (if present; nulls ranked after non-nulls)
         * 3. Tertiary: Local enqueue time ascending (FIFO)
         * 4. Tie-breaker: Lexicographical message ID
         */
        val RECORD_ORDER_COMPARATOR = Comparator<DurableQueueRecord> { a, b ->
            val timeCmp = a.timestamp.compareTo(b.timestamp)
            if (timeCmp != 0) return@Comparator timeCmp

            if (a.sequenceNumber != null && b.sequenceNumber != null) {
                val seqCmp = a.sequenceNumber.compareTo(b.sequenceNumber)
                if (seqCmp != 0) return@Comparator seqCmp
            } else if (a.sequenceNumber != null) {
                return@Comparator -1
            } else if (b.sequenceNumber != null) {
                return@Comparator 1
            }

            val enqueueCmp = a.enqueueTimeEpochMs.compareTo(b.enqueueTimeEpochMs)
            if (enqueueCmp != 0) return@Comparator enqueueCmp

            a.messageId.compareTo(b.messageId)
        }
    }
}
