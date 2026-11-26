package com.aerovital.phone.data.repository

import com.aerovital.phone.data.model.auth.AuthRequest
import com.aerovital.phone.data.remote.AuthApi
import com.aerovital.phone.data.remote.TokenManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.io.IOException

class AuthRepository(
    private val authApiProvider: () -> AuthApi,
    private val tokenManager: TokenManager
) {
    // Secondary constructor for backward compatibility with unit tests
    constructor(authApi: AuthApi, tokenManager: TokenManager) : this({ authApi }, tokenManager)

    private val authApi: AuthApi get() = authApiProvider()

    private val _authState = MutableStateFlow<AuthState>(AuthState.Unauthenticated)
    val authState: StateFlow<AuthState> = _authState.asStateFlow()

    init {
        checkExistingSession()
    }

    private fun checkExistingSession() {
        if (tokenManager.getToken() != null) {
            _authState.value = AuthState.Authenticating
        } else {
            _authState.value = AuthState.Unauthenticated
        }
    }

    suspend fun login(request: AuthRequest) {
        _authState.value = AuthState.Authenticating
        tokenManager.clearToken()
        try {
            val response = authApi.login(request)
            if (response.isSuccessful) {
                val body = response.body()
                if (body != null) {
                    tokenManager.saveToken(body.token)
                    _authState.value = AuthState.Authenticated(
                        username = body.username ?: request.username,
                        pilot = body.pilot
                    )
                } else {
                    _authState.value = AuthState.Error("Malformed response", ErrorType.MALFORMED_RESPONSE)
                }
            } else {
                when (response.code()) {
                    400 -> {
                        val errorString = response.errorBody()?.string() ?: "Bad request"
                        _authState.value = AuthState.Error(errorString, ErrorType.UNKNOWN)
                    }
                    401 -> _authState.value = AuthState.Error("Invalid credentials", ErrorType.INVALID_CREDENTIALS)
                    in 500..599 -> _authState.value = AuthState.Error("Backend unavailable", ErrorType.BACKEND_UNAVAILABLE)
                    else -> _authState.value = AuthState.Error("Login failed", ErrorType.UNKNOWN)
                }
            }
        } catch (e: IOException) {
            _authState.value = AuthState.Error("Network failure", ErrorType.NETWORK_FAILURE)
        } catch (e: Exception) {
            _authState.value = AuthState.Error(e.message ?: "Unknown error", ErrorType.UNKNOWN)
        }
    }

    suspend fun fetchMe() {
        if (tokenManager.getToken() == null) return
        
        try {
            val response = authApi.getMe()
            if (response.isSuccessful) {
                val body = response.body()
                if (body != null) {
                    _authState.value = AuthState.Authenticated(
                        username = body.username,
                        pilot = body.pilot
                    )
                } else {
                    _authState.value = AuthState.Error("Malformed response", ErrorType.MALFORMED_RESPONSE)
                }
            } else if (response.code() == 401) {
                handleUnauthorized()
            }
        } catch (e: IOException) {
            _authState.value = AuthState.Error("Network failure fetching profile", ErrorType.NETWORK_FAILURE)
        } catch (e: Exception) {
            _authState.value = AuthState.Error(e.message ?: "Unknown error", ErrorType.UNKNOWN)
        }
    }

    suspend fun logout() {
        try {
            authApi.logout()
        } catch (e: Exception) {
            // Ignore network errors on logout, we still want to clear local state
        } finally {
            tokenManager.clearToken()
            _authState.value = AuthState.Unauthenticated
        }
    }

    fun handleUnauthorized() {
        tokenManager.clearToken()
        _authState.value = AuthState.Error("Session invalid", ErrorType.SESSION_INVALID)
    }
}
