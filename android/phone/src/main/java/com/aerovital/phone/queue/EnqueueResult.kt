package com.aerovital.phone.queue

/**
 * Result representing the outcome of enqueuing an envelope into the durable queue.
 */
sealed class EnqueueResult {
    /**
     * Successfully enqueued into durable storage.
     */
    data class Enqueued(val messageId: String) : EnqueueResult()

    /**
     * Rejected because an envelope with this messageId is already in the queue.
     */
    data class Duplicate(val messageId: String) : EnqueueResult()

    /**
     * Rejected because queue capacity limit has been reached.
     * Prevents unbounded storage growth while keeping existing records safe.
     */
    data class QueueFull(val messageId: String, val capacity: Int) : EnqueueResult()

    /**
     * Rejected due to validation error prior to queuing.
     */
    data class Rejected(val reason: String) : EnqueueResult()

    val isEnqueued: Boolean
        get() = this is Enqueued
}
