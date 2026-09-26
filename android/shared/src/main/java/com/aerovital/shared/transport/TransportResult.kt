package com.aerovital.shared.transport

sealed class TransportResult<out T> {
    data class Success<out T>(val data: T) : TransportResult<T>()
    data class Error(val reason: ErrorReason, val message: String? = null) : TransportResult<Nothing>()
}

enum class ErrorReason {
    NO_NODES_CONNECTED,
    SEND_FAILED,
    MALFORMED_ENVELOPE,
    UNSUPPORTED_VERSION,
    DUPLICATE_MESSAGE,
    STALE_MESSAGE,
    FUTURE_TIMESTAMP,
    UNKNOWN_PAYLOAD_TYPE
}
