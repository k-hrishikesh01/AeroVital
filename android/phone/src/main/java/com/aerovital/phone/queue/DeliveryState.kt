package com.aerovital.phone.queue

/**
 * State machine representing the delivery status of a durable telemetry queue record.
 */
enum class DeliveryState {
    /**
     * Waiting in the queue to be dispatched to the backend.
     */
    PENDING,

    /**
     * Currently being transmitted over HTTP to Django.
     */
    IN_FLIGHT,

    /**
     * Delivery failed due to a transient error (e.g. network failure or HTTP 5xx).
     * Retained in queue with an exponential backoff retry scheduled.
     */
    FAILED_RETRYABLE,

    /**
     * Delivery failed due to authentication failure (HTTP 401/403).
     * Retained in queue; delivery paused until authentication is recovered.
     */
    AUTH_BLOCKED,

    /**
     * Terminal failure (e.g. non-retryable HTTP 4xx, malformed payload, or retry limit exceeded).
     * Retained in queue for diagnostic inspection; will not be automatically retried.
     */
    FAILED_TERMINAL,

    /**
     * Successfully delivered to Django backend and acknowledged with HTTP 200/201.
     */
    DELIVERED
}
