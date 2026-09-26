package com.aerovital.phone.data.remote

import com.aerovital.phone.data.model.telemetry.TelemetryIngestResponse

/**
 * Explicit result representing the outcome of a telemetry ingestion attempt.
 *
 * Distinguishes at minimum:
 * - successful HTTP delivery (Success)
 * - authentication failure (AuthenticationError)
 * - client failure (ClientError)
 * - network failure (NetworkError)
 * - server failure (ServerError)
 * - malformed/unusable telemetry payload (MalformedPayloadError)
 * - unexpected HTTP response (UnexpectedResponseError)
 */
sealed class TelemetryIngestResult {
    /**
     * Successful HTTP delivery (HTTP 200/201).
     */
    data class Success(
        val statusCode: Int,
        val response: TelemetryIngestResponse?
    ) : TelemetryIngestResult()

    /**
     * Authentication failure (HTTP 401/403 or missing token).
     */
    data class AuthenticationError(
        val statusCode: Int,
        val message: String
    ) : TelemetryIngestResult()

    /**
     * Client/request failure (HTTP 4xx other than 401/403).
     */
    data class ClientError(
        val statusCode: Int,
        val message: String
    ) : TelemetryIngestResult()

    /**
     * Server failure (HTTP 5xx).
     */
    data class ServerError(
        val statusCode: Int,
        val message: String
    ) : TelemetryIngestResult()

    /**
     * Network or connectivity failure (connection refused, timeout, host unreachable).
     */
    data class NetworkError(
        val exception: Throwable,
        val message: String = exception.message ?: "Network failure"
    ) : TelemetryIngestResult()

    /**
     * Malformed or unusable telemetry payload prior to transmission or serialization failure.
     */
    data class MalformedPayloadError(
        val reason: String
    ) : TelemetryIngestResult()

    /**
     * Unexpected HTTP response code.
     */
    data class UnexpectedResponseError(
        val statusCode: Int,
        val message: String
    ) : TelemetryIngestResult()

    val isSuccess: Boolean
        get() = this is Success
}
