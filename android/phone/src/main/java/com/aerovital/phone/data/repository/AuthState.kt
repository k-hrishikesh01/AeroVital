package com.aerovital.phone.data.repository

import com.aerovital.phone.data.model.auth.PilotProfile

sealed class AuthState {
    object Unauthenticated : AuthState()
    object Authenticating : AuthState()
    data class Authenticated(
        val username: String,
        val pilot: PilotProfile?
    ) : AuthState()
    data class Error(val message: String, val type: ErrorType) : AuthState()
}

enum class ErrorType {
    INVALID_CREDENTIALS,
    NETWORK_FAILURE,
    BACKEND_UNAVAILABLE,
    MALFORMED_RESPONSE,
    SESSION_INVALID,
    UNKNOWN
}
