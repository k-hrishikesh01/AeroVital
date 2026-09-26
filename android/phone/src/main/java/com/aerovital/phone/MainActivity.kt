package com.aerovital.phone

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.aerovital.phone.data.remote.ApiClient
import com.aerovital.phone.data.remote.TokenManager
import com.aerovital.phone.data.remote.SecureTokenManager
import com.aerovital.phone.data.repository.AuthRepository
import com.aerovital.phone.data.repository.AuthState
import com.aerovital.phone.ui.auth.AuthViewModel
import com.aerovital.phone.ui.auth.LoginScreen

class MainActivity : ComponentActivity() {

    private lateinit var authRepository: AuthRepository
    private lateinit var tokenManager: TokenManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        tokenManager = SecureTokenManager(applicationContext)
        authRepository = AuthRepository(
            authApi = ApiClient.getAuthApi(applicationContext) {
                authRepository.handleUnauthorized()
            },
            tokenManager = tokenManager
        )

        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val authViewModel: AuthViewModel = viewModel(
                        factory = AuthViewModel.Factory(authRepository)
                    )
                    
                    val authState by authViewModel.authState.collectAsStateWithLifecycle()
                    
                    when (authState) {
                        is AuthState.Authenticated -> {
                            val pilot = (authState as AuthState.Authenticated).pilot
                            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                                Text("Welcome, ${pilot?.name ?: "Unknown Pilot"}!")
                            }
                        }
                        else -> {
                            LoginScreen(
                                viewModel = authViewModel,
                                onLoginSuccess = { /* State transitions automatically */ }
                            )
                        }
                    }
                }
            }
        }
    }
}
