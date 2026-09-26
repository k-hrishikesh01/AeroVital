package com.aerovital.phone.data.remote

import android.util.Log
import com.aerovital.phone.BuildConfig
import com.aerovital.shared.telemetry.CanonicalTelemetry
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.io.IOException

/**
 * Authenticated HTTP client for ingesting CanonicalTelemetry into Django REST API.
 *
 * Configurable with any valid backend base URL and token provider.
 * Never hard-codes production URLs or credentials.
 * Never writes authentication tokens to logs.
 */
class DjangoTelemetryClient(
    private val telemetryApi: TelemetryApi,
    private val tokenProvider: TokenProvider? = null
) {
    /**
     * Sends a CanonicalTelemetry observation to Django REST API via POST /api/v1/telemetry/.
     *
     * @param telemetry The canonical telemetry to ingest.
     * @return Explicit TelemetryIngestResult distinguishing all outcome scenarios.
     */
    suspend fun sendTelemetry(telemetry: CanonicalTelemetry): TelemetryIngestResult {
        // Fast-fail if tokenProvider is present but has no valid authenticated token
        if (tokenProvider != null) {
            val token = tokenProvider.getToken()
            if (token.isNullOrBlank()) {
                return TelemetryIngestResult.AuthenticationError(
                    statusCode = 401,
                    message = "No authentication token available"
                )
            }
        }

        // Validate payload minimally before sending
        if (telemetry.timestamp.isBlank()) {
            return TelemetryIngestResult.MalformedPayloadError("Telemetry timestamp cannot be blank")
        }

        return try {
            val response = telemetryApi.ingestTelemetry(telemetry)
            val code = response.code()

            if (response.isSuccessful) {
                TelemetryIngestResult.Success(
                    statusCode = code,
                    response = response.body()
                )
            } else {
                val errorBody = response.errorBody()?.string().orEmpty()
                when (code) {
                    401, 403 -> TelemetryIngestResult.AuthenticationError(
                        statusCode = code,
                        message = if (errorBody.isNotBlank()) errorBody else "Authentication failed ($code)"
                    )
                    in 400..499 -> TelemetryIngestResult.ClientError(
                        statusCode = code,
                        message = if (errorBody.isNotBlank()) errorBody else "Client error ($code)"
                    )
                    in 500..599 -> TelemetryIngestResult.ServerError(
                        statusCode = code,
                        message = if (errorBody.isNotBlank()) errorBody else "Server error ($code)"
                    )
                    else -> TelemetryIngestResult.UnexpectedResponseError(
                        statusCode = code,
                        message = if (errorBody.isNotBlank()) errorBody else "Unexpected response ($code)"
                    )
                }
            }
        } catch (e: IOException) {
            TelemetryIngestResult.NetworkError(e, e.message ?: "Network failure")
        } catch (e: com.google.gson.JsonParseException) {
            TelemetryIngestResult.MalformedPayloadError("Serialization failure: ${e.message}")
        } catch (e: Exception) {
            TelemetryIngestResult.NetworkError(e, e.message ?: "Unexpected transmission error")
        }
    }

    companion object {
        private const val TAG = "DjangoTelemetryClient"

        /**
         * Factory method to construct a fully configured DjangoTelemetryClient.
         *
         * @param baseUrl The base URL of the Django backend (must be configurable).
         * @param tokenProvider The supplier of the authenticated token.
         * @param customOkHttpClient Optional OkHttpClient to override (useful for testing).
         */
        fun create(
            baseUrl: String,
            tokenProvider: TokenProvider,
            customOkHttpClient: OkHttpClient? = null
        ): DjangoTelemetryClient {
            val normalizedBaseUrl = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"

            val okHttpClient = customOkHttpClient ?: run {
                val loggingInterceptor = HttpLoggingInterceptor().apply {
                    level = if (BuildConfig.DEBUG) {
                        HttpLoggingInterceptor.Level.HEADERS
                    } else {
                        HttpLoggingInterceptor.Level.NONE
                    }
                    // Crucial security requirement: NEVER log authentication tokens
                    redactHeader("Authorization")
                }

                val authInterceptor = Interceptor { chain ->
                    val requestBuilder = chain.request().newBuilder()
                    tokenProvider.getToken()?.let { token ->
                        requestBuilder.addHeader("Authorization", "Token $token")
                    }
                    chain.proceed(requestBuilder.build())
                }

                OkHttpClient.Builder()
                    .addInterceptor(authInterceptor)
                    .addInterceptor(loggingInterceptor)
                    .build()
            }

            val retrofit = Retrofit.Builder()
                .baseUrl(normalizedBaseUrl)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()

            return DjangoTelemetryClient(
                telemetryApi = retrofit.create(TelemetryApi::class.java),
                tokenProvider = tokenProvider
            )
        }
    }
}
