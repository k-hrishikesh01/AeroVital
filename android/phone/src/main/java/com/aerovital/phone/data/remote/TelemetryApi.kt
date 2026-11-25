package com.aerovital.phone.data.remote

import com.aerovital.phone.data.model.telemetry.TelemetryDto
import com.aerovital.phone.data.model.telemetry.TelemetryIngestResponse
import com.aerovital.shared.telemetry.CanonicalTelemetry
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

/**
 * Retrofit API interface for AeroVital Django telemetry ingestion and query endpoints.
 */
interface TelemetryApi {
    @POST("api/v1/telemetry/")
    suspend fun ingestTelemetry(
        @Body telemetry: CanonicalTelemetry
    ): Response<TelemetryIngestResponse>

    @GET("api/v1/telemetry/")
    suspend fun getTelemetry(
        @Query("limit") limit: Int = 10,
        @Query("has_hr") hasHr: Boolean? = true
    ): Response<List<TelemetryDto>>
}
