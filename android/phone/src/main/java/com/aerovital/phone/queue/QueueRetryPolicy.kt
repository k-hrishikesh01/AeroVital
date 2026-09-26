package com.aerovital.phone.queue

import com.aerovital.phone.data.remote.TelemetryIngestResult

/**
 * Engineering parameters governing the store-and-forward queue's retry and capacity behavior.
 *
 * Parameters:
 * @param initialBackoffMs Initial delay before the first retry attempt (Default: 1,000 ms).
 * @param backoffMultiplier Exponential factor applied to each successive retry (Default: 2.0).
 * @param maxBackoffMs Upper ceiling on retry backoff delay (Default: 60,000 ms = 1 minute).
 * @param maxDeliveryAttempts Maximum delivery attempts before moving to FAILED_TERMINAL dead-letter state (Default: 5).
 * @param maxQueueCapacity Maximum records permitted in the queue to safeguard device flash storage (Default: 10,000).
 */
data class QueueRetryPolicy(
    val initialBackoffMs: Long = 1_000L,
    val backoffMultiplier: Double = 2.0,
    val maxBackoffMs: Long = 60_000L,
    val maxDeliveryAttempts: Int = 5,
    val maxQueueCapacity: Int = 10_000
) {
    /**
     * Computes the deterministic exponential backoff delay in milliseconds for a given attempt.
     * Attempt 1 -> initialBackoffMs (1s)
     * Attempt 2 -> 2s
     * Attempt 3 -> 4s
     * Attempt 4 -> 8s
     * Attempt 5 -> 16s
     * Capped at maxBackoffMs (60s).
     */
    fun computeBackoffDelayMs(attemptNumber: Int): Long {
        if (attemptNumber <= 0) return 0L
        val exponential = (initialBackoffMs * Math.pow(backoffMultiplier, (attemptNumber - 1).toDouble())).toLong()
        return exponential.coerceAtMost(maxBackoffMs)
    }

    /**
     * Determines whether a TelemetryIngestResult qualifies as a transient, retryable failure.
     *
     * Retryable:
     * - NetworkError (connection dropped, DNS lookup failed, timeout)
     * - ServerError (HTTP 5xx from backend)
     *
     * Non-retryable:
     * - AuthenticationError (HTTP 401/403: blocked until token recovery, handled by AUTH_BLOCKED)
     * - ClientError (HTTP 4xx: schema or physiological validation failure; terminal)
     * - MalformedPayloadError (terminal)
     * - UnexpectedResponseError (terminal)
     * - Success (already successful)
     */
    fun isRetryable(result: TelemetryIngestResult): Boolean {
        return when (result) {
            is TelemetryIngestResult.NetworkError -> true
            is TelemetryIngestResult.ServerError -> true
            is TelemetryIngestResult.AuthenticationError -> false
            is TelemetryIngestResult.ClientError -> false
            is TelemetryIngestResult.MalformedPayloadError -> false
            is TelemetryIngestResult.UnexpectedResponseError -> false
            is TelemetryIngestResult.Success -> false
        }
    }
}
