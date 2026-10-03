package com.aerovital.phone

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.graphics.toArgb
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
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
import com.aerovital.phone.ui.dashboard.DashboardScreen
import com.aerovital.phone.ui.details.DetailsScreen
import com.aerovital.phone.ui.diagnostic.PhoneDiagnosticScreen
import com.aerovital.phone.ui.history.HistoryScreen
import com.aerovital.phone.ui.navigation.AppScreen
import com.aerovital.phone.ui.profile.ProfileScreen
import com.aerovital.phone.ui.settings.SettingsScreen
import androidx.compose.ui.platform.LocalContext
import com.aerovital.phone.ui.theme.AeroBackground
import com.aerovital.phone.ui.theme.AeroDarkBackground
import com.aerovital.phone.ui.theme.AeroDarkNavy
import com.aerovital.phone.ui.theme.AeroVitalTheme
import com.aerovital.phone.ui.theme.ThemePreferences

class MainActivity : ComponentActivity() {

    private lateinit var authRepository: AuthRepository
    private lateinit var tokenManager: TokenManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val initialDarkMode = ThemePreferences.isDarkMode(applicationContext)
        val statusColor = if (initialDarkMode) AeroDarkBackground.toArgb() else AeroBackground.toArgb()
        val navColor = if (initialDarkMode) AeroDarkBackground.toArgb() else AeroBackground.toArgb()
        val statusStyle = if (initialDarkMode) {
            SystemBarStyle.dark(statusColor)
        } else {
            SystemBarStyle.light(statusColor, AeroDarkNavy.toArgb())
        }
        val navStyle = if (initialDarkMode) {
            SystemBarStyle.dark(navColor)
        } else {
            SystemBarStyle.light(navColor, AeroDarkNavy.toArgb())
        }
        enableEdgeToEdge(statusStyle, navStyle)

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
            val context = LocalContext.current
            var isDarkMode by rememberSaveable { mutableStateOf(ThemePreferences.isDarkMode(context)) }

            AeroVitalTheme(darkTheme = isDarkMode) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val authViewModel: AuthViewModel = viewModel(
                        factory = AuthViewModel.Factory(authRepository)
                    )
                    
                    val authState by authViewModel.authState.collectAsStateWithLifecycle()
                    var currentScreen by rememberSaveable { mutableStateOf(AppScreen.DASHBOARD) }

                    when (authState) {
                        is AuthState.Authenticated -> {
                            val auth = authState as AuthState.Authenticated

                            if (currentScreen != AppScreen.DASHBOARD) {
                                BackHandler {
                                    currentScreen = AppScreen.DASHBOARD
                                }
                            }

                            when (currentScreen) {
                                AppScreen.DASHBOARD -> {
                                    DashboardScreen(
                                        username = auth.username,
                                        pilot = auth.pilot,
                                        onNavigate = { destination ->
                                            currentScreen = destination
                                        },
                                        onLogoutClick = {
                                            authViewModel.logout()
                                            currentScreen = AppScreen.DASHBOARD
                                        }
                                    )
                                }
                                AppScreen.DETAILS -> {
                                    DetailsScreen(
                                        username = auth.username,
                                        pilot = auth.pilot,
                                        onBack = { currentScreen = AppScreen.DASHBOARD },
                                        onDiagnosticsClick = { currentScreen = AppScreen.DIAGNOSTICS }
                                    )
                                }
                                AppScreen.HISTORY -> {
                                    HistoryScreen(
                                        pilotCode = auth.pilot?.pilotCode ?: "--",
                                        onBack = { currentScreen = AppScreen.DASHBOARD }
                                    )
                                }
                                AppScreen.PROFILE -> {
                                    ProfileScreen(
                                        username = auth.username,
                                        pilot = auth.pilot,
                                        onBack = { currentScreen = AppScreen.DASHBOARD },
                                        onSettingsClick = { currentScreen = AppScreen.SETTINGS },
                                        onLogoutClick = {
                                            authViewModel.logout()
                                            currentScreen = AppScreen.DASHBOARD
                                        }
                                    )
                                }
                                AppScreen.SETTINGS -> {
                                    SettingsScreen(
                                        username = auth.username,
                                        pilot = auth.pilot,
                                        isDarkMode = isDarkMode,
                                        onDarkModeChanged = { enabled ->
                                            isDarkMode = enabled
                                            ThemePreferences.setDarkMode(context, enabled)
                                        },
                                        onBack = { currentScreen = AppScreen.DASHBOARD },
                                        onDiagnosticsClick = { currentScreen = AppScreen.DIAGNOSTICS },
                                        onLogoutClick = {
                                            authViewModel.logout()
                                            currentScreen = AppScreen.DASHBOARD
                                        }
                                    )
                                }
                                AppScreen.DIAGNOSTICS -> {
                                    PhoneDiagnosticScreen(
                                        username = auth.username,
                                        pilot = auth.pilot,
                                        onLogout = {
                                            authViewModel.logout()
                                            currentScreen = AppScreen.DASHBOARD
                                        },
                                        onBack = { currentScreen = AppScreen.DASHBOARD }
                                    )
                                }
                            }
                        }
                        else -> {
                            LoginScreen(
                                viewModel = authViewModel,
                                onLoginSuccess = {
                                    currentScreen = AppScreen.DASHBOARD
                                }
                            )
                        }
                    }
                }
            }
        }
    }
}
