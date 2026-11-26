package com.aerovital.shared.transport

import com.google.gson.Gson
import com.google.gson.annotations.SerializedName

/**
 * Explicit application-level acknowledgement sent from the phone to the watch
 * after a telemetry batch has been durably persisted in the phone-side queue.
 */
data class TelemetryAck(
    @SerializedName("messageId") val messageId: String,
    @SerializedName("batchId") val batchId: String? = null,
    @SerializedName("sequenceNumber") val sequenceNumber: Long? = null,
    @SerializedName("status") val status: String = STATUS_STORED,
    @SerializedName("timestamp") val timestamp: Long = System.currentTimeMillis()
) {
    fun toJson(gson: Gson = Gson()): String = gson.toJson(this)

    companion object {
        const val STATUS_STORED = "STORED"
        const val STATUS_DUPLICATE = "DUPLICATE"
        const val STATUS_REJECTED = "REJECTED"

        fun fromJson(json: String, gson: Gson = Gson()): TelemetryAck? {
            return try {
                gson.fromJson(json, TelemetryAck::class.java)
            } catch (e: Exception) {
                null
            }
        }
    }
}
