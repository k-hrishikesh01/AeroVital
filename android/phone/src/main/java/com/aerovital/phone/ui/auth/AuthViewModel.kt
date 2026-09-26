package com.aerovital.phone.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.aerovital.phone.data.model.auth.AuthRequest
import com.aerovital.phone.data.repository.AuthRepository
import com.aerovital.phone.data.repository.AuthState
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class AuthViewModel(
    private val repository: AuthRepository
) : ViewModel() {

    val authState: StateFlow<AuthState> = repository.authState

    init {
        // If we initialized into Authenticating state because a token exists, fetch profile
        if (authState.value is AuthState.Authenticating) {
            viewModelScope.launch {
                repository.fetchMe()
            }
        }
    }

    fun login(request: AuthRequest) {
        viewModelScope.launch {
            repository.login(request)
        }
    }

    fun logout() {
        viewModelScope.launch {
            repository.logout()
        }
    }

    class Factory(private val repository: AuthRepository) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            if (modelClass.isAssignableFrom(AuthViewModel::class.java)) {
                return AuthViewModel(repository) as T
            }
            throw IllegalArgumentException("Unknown ViewModel class")
        }
    }
}
