package com.example.aerovital.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.aerovital.data.repository.AuthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

sealed class AuthUiState {
    object Idle : AuthUiState()
    object Loading : AuthUiState()
    data class Authenticated(val pilotId: String) : AuthUiState()
    data class Error(val message: String) : AuthUiState()
    data class PasswordResetSuccess(val message: String) : AuthUiState()
}

class AuthViewModel(
    private val authRepository: AuthRepository = AuthRepository()
) : ViewModel() {

    private val _uiState = MutableStateFlow<AuthUiState>(AuthUiState.Idle)
    val uiState: StateFlow<AuthUiState> = _uiState

    init {
        checkAuthStatus()
    }

    fun checkAuthStatus() {
        val pilotId = authRepository.getCurrentPilotId()
        if (pilotId != null) {
            _uiState.value = AuthUiState.Authenticated(pilotId)
        } else {
            _uiState.value = AuthUiState.Idle
        }
    }

    fun login(pilotId: String, password: String) {
        if (pilotId.isBlank()) {
            _uiState.value = AuthUiState.Error("Please enter your Pilot ID.")
            return
        }
        if (password.isBlank()) {
            _uiState.value = AuthUiState.Error("Please enter your password.")
            return
        }

        _uiState.value = AuthUiState.Loading

        viewModelScope.launch {
            val result = authRepository.login(pilotId, password)
            result.onSuccess { authenticatedId ->
                _uiState.value = AuthUiState.Authenticated(authenticatedId)
            }.onFailure { exception ->
                _uiState.value = AuthUiState.Error(
                    exception.message ?: "Login failed. Please check your Pilot ID and password."
                )
            }
        }
    }

    fun signUp(
        fullName: String,
        pilotId: String,
        password: String,
        confirmPassword: String
    ) {
        if (fullName.isBlank()) {
            _uiState.value = AuthUiState.Error("Please enter your Full Name.")
            return
        }
        if (pilotId.isBlank()) {
            _uiState.value = AuthUiState.Error("Please enter a valid Pilot ID (e.g., AVP-2026-001).")
            return
        }

        // Validate password requirements
        val passwordValidationError = validatePassword(password)
        if (passwordValidationError != null) {
            _uiState.value = AuthUiState.Error(passwordValidationError)
            return
        }

        if (password != confirmPassword) {
            _uiState.value = AuthUiState.Error("Passwords do not match.")
            return
        }

        _uiState.value = AuthUiState.Loading

        viewModelScope.launch {
            val result = authRepository.register(fullName, pilotId, password)
            result.onSuccess { registeredId ->
                _uiState.value = AuthUiState.Authenticated(registeredId)
            }.onFailure { exception ->
                _uiState.value = AuthUiState.Error(
                    exception.message ?: "Account creation failed."
                )
            }
        }
    }

    fun resetPassword(pilotId: String, newPassword: String, confirmNewPassword: String) {
        if (pilotId.isBlank()) {
            _uiState.value = AuthUiState.Error("Please enter your Pilot ID.")
            return
        }

        val passwordValidationError = validatePassword(newPassword)
        if (passwordValidationError != null) {
            _uiState.value = AuthUiState.Error(passwordValidationError)
            return
        }

        if (newPassword != confirmNewPassword) {
            _uiState.value = AuthUiState.Error("Passwords do not match.")
            return
        }

        _uiState.value = AuthUiState.Loading

        viewModelScope.launch {
            val result = authRepository.resetPassword(pilotId, newPassword)
            result.onSuccess {
                _uiState.value = AuthUiState.PasswordResetSuccess("Password successfully updated. Please login.")
            }.onFailure { exception ->
                _uiState.value = AuthUiState.Error(
                    exception.message ?: "Failed to reset password."
                )
            }
        }
    }

    fun logout() {
        authRepository.signOut()
        _uiState.value = AuthUiState.Idle
    }

    fun clearError() {
        if (_uiState.value is AuthUiState.Error) {
            _uiState.value = AuthUiState.Idle
        }
    }

    private fun validatePassword(password: String): String? {
        if (password.length < 8) {
            return "Password must be at least 8 characters long."
        }
        if (!password.any { it.isUpperCase() }) {
            return "Password must contain at least 1 uppercase letter."
        }
        if (!password.any { it.isLowerCase() }) {
            return "Password must contain at least 1 lowercase letter."
        }
        if (!password.any { it.isDigit() }) {
            return "Password must contain at least 1 number."
        }
        val specialCharRegex = Regex("[!@#$%^&*()_+\\-=\\[\\]{};':\"\\\\|,.<>/?]")
        if (!specialCharRegex.containsMatchIn(password)) {
            return "Password must contain at least 1 special character (e.g. @, #, $)."
        }
        return null
    }
}
