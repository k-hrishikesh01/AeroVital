package com.aerovital.phone.data.remote

import com.aerovital.phone.data.model.telemetry.TelemetryIngestResponse
import com.aerovital.shared.telemetry.CanonicalTelemetry
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.POST

/**
 * Retrofit API interface for AeroVital Django telemetry ingestion endpoint.
 */
interface TelemetryApi {
    @POST("api/v1/telemetry/")
    suspend fun ingestTelemetry(
        @Body telemetry: CanonicalTelemetry
    ): Response<TelemetryIngestResponse>
}
