package com.aerovital.shared.transport

import com.aerovital.shared.telemetry.CanonicalTelemetry
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName

/**
 * Batched payload containing multiple CanonicalTelemetry samples.
 * Used for 5-10 second batching to dramatically reduce wearable radio awake-cycles.
 */
data class TelemetryBatch(
    @SerializedName("batchId") val batchId: String,
    @SerializedName("samples") val samples: List<CanonicalTelemetry>,
    @SerializedName("batchTimestamp") val batchTimestamp: Long = System.currentTimeMillis()
) {
    fun toJson(gson: Gson = Gson()): String = gson.toJson(this)

    companion object {
        fun fromJson(json: String, gson: Gson = Gson()): TelemetryBatch? {
            return try {
                gson.fromJson(json, TelemetryBatch::class.java)
            } catch (e: Exception) {
                null
            }
        }
    }
}
