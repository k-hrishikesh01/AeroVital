package com.aerovital.phone.queue

import android.util.Log
import com.aerovital.phone.BuildConfig
import com.aerovital.phone.data.remote.DjangoTelemetryClient
import com.aerovital.phone.data.remote.TelemetryIngestResult
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

/**
 * Summary of outcomes for a queue drainage cycle.
 */
data class QueueDrainSummary(
    val processedCount: Int = 0,
    val successCount: Int = 0,
    val retryableFailureCount: Int = 0,
    val terminalFailureCount: Int = 0,
    val authBlockedCount: Int = 0,
    val lastResult: TelemetryIngestResult? = null
)

/**
 * Delivery worker and queue coordinator.
 *
 * Reads pending records in deterministic order from [queue] and dispatches them
 * using the existing A5 [telemetryClient].
 *
 * Enforces:
 * - Deterministic ordering (chronological replay by observation timestamp)
 * - Atomic removal on confirmed delivery
 * - Bounded exponential backoff on transient errors
 * - Dead-lettering to FAILED_TERMINAL on max attempts or non-retryable 4xx
 * - AUTH_BLOCKED handling on 401/403 to prevent unauthenticated hammering
 */
class TelemetryDeliveryCoordinator(
    private val queue: TelemetryQueue,
    private val telemetryClient: DjangoTelemetryClient,
    private val retryPolicy: QueueRetryPolicy = QueueRetryPolicy()
) {
    private val drainMutex = Mutex()

    /**
     * Drains pending records from the queue up to [batchLimit].
     *
     * Ensures only one drain loop executes at any given time via [drainMutex].
     */
    suspend fun drainQueue(
        batchLimit: Int = 50,
        currentEpochMs: Long = System.currentTimeMillis()
    ): QueueDrainSummary = drainMutex.withLock {
        var processed = 0
        var successCount = 0
        var retryableCount = 0
        var terminalCount = 0
        var authBlockedCount = 0
        var lastResult: TelemetryIngestResult? = null

        val pendingRecords = queue.peekPending(batchLimit, currentEpochMs)

        for (record in pendingRecords) {
            processed += 1
            queue.markInFlight(record.messageId)

            val telemetry = record.toCanonicalTelemetry()
            if (telemetry == null) {
                // Cannot deserialize canonical telemetry from envelope payload
                queue.markTerminalFailure(
                    messageId = record.messageId,
                    classification = "MALFORMED_CANONICAL_PAYLOAD",
                    message = "Failed to deserialize CanonicalTelemetry from envelope"
                )
                terminalCount += 1
                lastResult = TelemetryIngestResult.MalformedPayloadError("Deserialization failed")
                continue
            }

            val result = telemetryClient.sendTelemetry(telemetry)
            lastResult = result

            when (result) {
                is TelemetryIngestResult.Success -> {
                    // Confirmed delivery: remove from durable queue
                    queue.markSuccess(record.messageId)
                    successCount += 1
                    if (BuildConfig.DEBUG) {
                        Log.d(TAG, "Delivered message ${record.messageId} (status ${result.statusCode})")
                    }
                }

                is TelemetryIngestResult.AuthenticationError -> {
                    // HTTP 401/403 or missing token: retain telemetry, block queue
                    val classification = "AUTH_ERROR_${result.statusCode}"
                    queue.markAuthBlocked(
                        messageId = record.messageId,
                        classification = classification,
                        message = result.message
                    )
                    authBlockedCount += 1
                    if (BuildConfig.DEBUG) {
                        Log.w(TAG, "Auth blocked on message ${record.messageId}: ${result.message}. Pausing queue drain.")
                    }
                    // Stop queue drain until authentication recovers
                    break
                }

                is TelemetryIngestResult.NetworkError -> {
                    val wasRetryable = handleTransientFailure(record, "NETWORK_ERROR", result.message)
                    if (wasRetryable) retryableCount += 1 else terminalCount += 1
                    if (BuildConfig.DEBUG) {
                        Log.w(TAG, "Transient network failure on message ${record.messageId}: ${result.message}. Pausing queue drain.")
                    }
                    break
                }

                is TelemetryIngestResult.ServerError -> {
                    val wasRetryable = handleTransientFailure(record, "SERVER_ERROR_${result.statusCode}", result.message)
                    if (wasRetryable) retryableCount += 1 else terminalCount += 1
                    if (BuildConfig.DEBUG) {
                        Log.w(TAG, "Transient server failure on message ${record.messageId}: ${result.message}. Pausing queue drain.")
                    }
                    break
                }

                is TelemetryIngestResult.ClientError -> {
                    // Non-retryable 4xx (e.g. 400 Bad Request): transition to FAILED_TERMINAL
                    queue.markTerminalFailure(
                        messageId = record.messageId,
                        classification = "CLIENT_ERROR_${result.statusCode}",
                        message = result.message
                    )
                    terminalCount += 1
                    if (BuildConfig.DEBUG) {
                        Log.e(TAG, "Non-retryable client error on message ${record.messageId}: ${result.message}")
                    }
                    // Non-retryable payload error does not block other valid items
                }

                is TelemetryIngestResult.MalformedPayloadError -> {
                    queue.markTerminalFailure(
                        messageId = record.messageId,
                        classification = "MALFORMED_PAYLOAD",
                        message = result.reason
                    )
                    terminalCount += 1
                }

                is TelemetryIngestResult.UnexpectedResponseError -> {
                    queue.markTerminalFailure(
                        messageId = record.messageId,
                        classification = "UNEXPECTED_RESPONSE_${result.statusCode}",
                        message = result.message
                    )
                    terminalCount += 1
                }
            }
        }

        QueueDrainSummary(
            processedCount = processed,
            successCount = successCount,
            retryableFailureCount = retryableCount,
            terminalFailureCount = terminalCount,
            authBlockedCount = authBlockedCount,
            lastResult = lastResult
        )
    }

    private fun handleTransientFailure(
        record: DurableQueueRecord,
        classification: String,
        errorMessage: String
    ): Boolean {
        val newAttempt = record.attemptCount + 1
        return if (newAttempt >= retryPolicy.maxDeliveryAttempts) {
            queue.markTerminalFailure(
                messageId = record.messageId,
                classification = classification,
                message = "Exceeded max attempts (${retryPolicy.maxDeliveryAttempts}): $errorMessage"
            )
            false
        } else {
            val backoffDelay = retryPolicy.computeBackoffDelayMs(newAttempt)
            queue.markRetryableFailure(
                messageId = record.messageId,
                classification = classification,
                message = errorMessage,
                delayMs = backoffDelay
            )
            true
        }
    }

    /**
     * Unblocks any records that were marked AUTH_BLOCKED back to PENDING.
     * Called when the pilot logs in or token is refreshed.
     */
    fun onAuthenticationRecovered() {
        val allRecords = queue.getAllRecords()
        for (record in allRecords) {
            if (record.deliveryState == DeliveryState.AUTH_BLOCKED) {
                record.deliveryState = DeliveryState.PENDING
                record.nextRetryEpochMs = null
            }
        }
    }

    companion object {
        private const val TAG = "TelemetryDeliveryWorker"
    }
}
