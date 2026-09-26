package com.aerovital.phone.data.model.telemetry

import com.google.gson.annotations.SerializedName

/**
 * Response model returned by Django REST API upon POST /api/v1/telemetry/.
 *
 * Reflects the backend response structure containing the persisted telemetry record,
 * pipeline status ("accumulating" or "evaluated"), and optional estimation, quality, and alert details.
 */
data class TelemetryIngestResponse(
    @SerializedName("telemetry") val telemetry: Map<String, Any?>? = null,
    @SerializedName("status") val status: String? = null,
    @SerializedName("estimate") val estimate: Map<String, Any?>? = null,
    @SerializedName("quality") val quality: Map<String, Any?>? = null,
    @SerializedName("alert") val alert: Map<String, Any?>? = null
)
