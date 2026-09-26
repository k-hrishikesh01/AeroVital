package com.aerovital.phone

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.aerovital.phone.data.remote.ApiClient
import com.aerovital.phone.data.remote.DevBackendConfig
import com.aerovital.phone.data.remote.SecureTokenManager
import com.aerovital.phone.data.remote.TokenManager
import com.aerovital.phone.data.repository.AuthRepository
import com.aerovital.phone.data.repository.AuthState
import com.aerovital.phone.transport.WearTransportReceiver
import com.aerovital.phone.ui.auth.AuthViewModel
import com.aerovital.phone.ui.auth.LoginScreen
import com.aerovital.phone.ui.diagnostic.PhoneDiagnosticScreen

class MainActivity : ComponentActivity() {

    private lateinit var authRepository: AuthRepository
    private lateinit var tokenManager: TokenManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Initialize development backend configuration
        DevBackendConfig.init(applicationContext)

        // Ensure background transport receiver handler is eagerly prepared
        WearTransportReceiver.getOrInitHandler(applicationContext)

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
                            val auth = authState as AuthState.Authenticated
                            PhoneDiagnosticScreen(
                                username = auth.username,
                                pilot = auth.pilot,
                                onLogout = { authViewModel.logout() }
                            )
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
