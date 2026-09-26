package com.aerovital.phone.queue

import com.aerovital.shared.transport.TransportEnvelope

/**
 * Interface defining durable queue operations for store-and-forward telemetry.
 */
interface TelemetryQueue {
    /**
     * Enqueues an envelope durably into the queue.
     * Rejects duplicate messageIds and enforces queue capacity limits.
     */
    fun enqueue(envelope: TransportEnvelope): EnqueueResult

    /**
     * Retrieves pending records eligible for transmission, ordered deterministically.
     * Records with nextRetryEpochMs > currentEpochMs are excluded until their backoff expires.
     */
    fun peekPending(limit: Int = 50, currentEpochMs: Long = System.currentTimeMillis()): List<DurableQueueRecord>

    /**
     * Retrieves a single record by its messageId.
     */
    fun getRecord(messageId: String): DurableQueueRecord?

    /**
     * Marks a record as in-flight during active HTTP transmission.
     */
    fun markInFlight(messageId: String): Boolean

    /**
     * Confirms successful delivery and removes the record from durable storage.
     */
    fun markSuccess(messageId: String): Boolean

    /**
     * Marks a record as transiently failed, incrementing attempts and scheduling exponential backoff.
     */
    fun markRetryableFailure(
        messageId: String,
        classification: String,
        message: String?,
        delayMs: Long,
        attemptEpochMs: Long = System.currentTimeMillis()
    ): Boolean

    /**
     * Marks a record as blocked due to authentication failure (HTTP 401/403).
     * Retains the record until authentication is recovered.
     */
    fun markAuthBlocked(
        messageId: String,
        classification: String,
        message: String?,
        attemptEpochMs: Long = System.currentTimeMillis()
    ): Boolean

    /**
     * Marks a record as terminally failed (e.g. non-retryable 4xx or retry limit reached).
     * Retains the record as dead-letter diagnostic data without endless retrying.
     */
    fun markTerminalFailure(
        messageId: String,
        classification: String,
        message: String?,
        attemptEpochMs: Long = System.currentTimeMillis()
    ): Boolean

    /**
     * Counts pending and eligible retryable records waiting for delivery.
     */
    fun countPending(): Int

    /**
     * Counts all records currently held in durable storage across all states.
     */
    fun countTotal(): Int

    /**
     * Returns all records currently held in durable storage.
     */
    fun getAllRecords(): List<DurableQueueRecord>

    /**
     * Clears all records (primarily for testing and controlled cleanup).
     */
    fun clear()

    /**
     * Returns a snapshot diagnostic summary of queue counts by delivery state.
     */
    fun getDiagnosticSummary(): QueueDiagnosticSummary
}

/**
 * Read-only diagnostic summary of telemetry queue states.
 */
data class QueueDiagnosticSummary(
    val pendingCount: Int = 0,
    val inFlightCount: Int = 0,
    val retryableCount: Int = 0,
    val authBlockedCount: Int = 0,
    val terminalCount: Int = 0,
    val totalCount: Int = 0,
    val oldestPendingEpochMs: Long? = null,
    val newestPendingEpochMs: Long? = null
)
