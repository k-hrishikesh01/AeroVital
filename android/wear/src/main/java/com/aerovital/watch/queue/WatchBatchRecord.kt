package com.aerovital.watch.queue

import com.aerovital.shared.transport.TransportEnvelope
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName

/**
 * Record representing a telemetry batch persisted durably on the watch.
 * Retained until confirmed by an application-level ACK from the phone.
 */
data class WatchBatchRecord(
    @SerializedName("messageId") val messageId: String,
    @SerializedName("batchId") val batchId: String,
    @SerializedName("sequenceNumber") val sequenceNumber: Long,
    @SerializedName("timestamp") val timestamp: Long,
    @SerializedName("envelopeJson") val envelopeJson: String,
    @SerializedName("attemptCount") var attemptCount: Int = 0,
    @SerializedName("lastAttemptEpochMs") var lastAttemptEpochMs: Long? = null,
    @SerializedName("nextRetryEpochMs") var nextRetryEpochMs: Long? = null,
    @SerializedName("isAcknowledged") var isAcknowledged: Boolean = false
) {
    fun toTransportEnvelope(gson: Gson = Gson()): TransportEnvelope? {
        return try {
            gson.fromJson(envelopeJson, TransportEnvelope::class.java)
        } catch (e: Exception) {
            null
        }
    }

    companion object {
        val CHRONOLOGICAL_COMPARATOR: Comparator<WatchBatchRecord> =
            Comparator { a, b ->
                val seqCompare = a.sequenceNumber.compareTo(b.sequenceNumber)
                if (seqCompare != 0) seqCompare else a.timestamp.compareTo(b.timestamp)
            }

        fun fromEnvelope(
            envelope: TransportEnvelope,
            gson: Gson = Gson()
        ): WatchBatchRecord {
            return WatchBatchRecord(
                messageId = envelope.messageId,
                batchId = envelope.batchId ?: envelope.messageId,
                sequenceNumber = envelope.sequenceNumber ?: 0L,
                timestamp = envelope.timestamp,
                envelopeJson = gson.toJson(envelope)
            )
        }
    }
}
