package com.example.aerovital

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.aerovital.data.model.PilotProfile
import com.example.aerovital.ui.DashboardScreen
import com.example.aerovital.ui.DetailsScreen
import com.example.aerovital.ui.ForgotPasswordScreen
import com.example.aerovital.ui.HistoryScreen
import com.example.aerovital.ui.LoginScreen
import com.example.aerovital.ui.ProfileScreen
import com.example.aerovital.ui.SettingsScreen
import com.example.aerovital.ui.SignUpScreen
import com.example.aerovital.ui.theme.AeroVitalTheme
import com.example.aerovital.ui.viewmodel.AuthUiState
import com.example.aerovital.ui.viewmodel.AuthViewModel
import com.example.aerovital.ui.viewmodel.PilotUiState
import com.example.aerovital.ui.viewmodel.PilotViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AeroVitalApp()
        }
    }
}

enum class AppScreen {
    LOGIN,
    SIGN_UP,
    FORGOT_PASSWORD,
    DASHBOARD,
    PROFILE,
    DETAILS,
    HISTORY,
    SETTINGS
}

@Composable
fun AeroVitalApp(
    authViewModel: AuthViewModel = viewModel(),
    pilotViewModel: PilotViewModel = viewModel()
) {
    var currentScreen by remember { mutableStateOf(AppScreen.LOGIN) }
    var currentPilotId by remember { mutableStateOf("") }

    val authState by authViewModel.uiState.collectAsState()
    val pilotState by pilotViewModel.pilotState.collectAsState()

    // Automatic Authentication State Check on App Startup
    LaunchedEffect(authState) {
        when (val state = authState) {
            is AuthUiState.Authenticated -> {
                currentPilotId = state.pilotId
                pilotViewModel.loadPilotData(state.pilotId)
                currentScreen = AppScreen.DASHBOARD
            }
            is AuthUiState.Idle -> {
                if (currentScreen != AppScreen.SIGN_UP && currentScreen != AppScreen.FORGOT_PASSWORD) {
                    currentScreen = AppScreen.LOGIN
                }
            }
            else -> {}
        }
    }

    // Android Back Button Navigation Guard
    BackHandler(enabled = true) {
        when (currentScreen) {
            AppScreen.DASHBOARD -> {
                // On Dashboard back press, minimize or stay on Dashboard
            }
            AppScreen.LOGIN -> {
                // Exit app
            }
            AppScreen.SIGN_UP, AppScreen.FORGOT_PASSWORD -> {
                authViewModel.clearError()
                currentScreen = AppScreen.LOGIN
            }
            AppScreen.PROFILE, AppScreen.DETAILS, AppScreen.HISTORY, AppScreen.SETTINGS -> {
                currentScreen = AppScreen.DASHBOARD
            }
        }
    }

    val activeProfile = when (val state = pilotState) {
        is PilotUiState.Success -> state.profile
        else -> PilotProfile(pilotId = currentPilotId)
    }

    val historyList = when (val state = pilotState) {
        is PilotUiState.Success -> state.history
        else -> emptyList()
    }

    AeroVitalTheme {
        when (currentScreen) {

            /*
             * LOGIN SCREEN
             */
            AppScreen.LOGIN -> {
                val isLoading = authState is AuthUiState.Loading
                val errorMessage = (authState as? AuthUiState.Error)?.message

                LoginScreen(
                    onLogin = { pilotId, password ->
                        authViewModel.clearError()
                        authViewModel.login(pilotId, password)
                    },
                    onForgotPassword = {
                        authViewModel.clearError()
                        currentScreen = AppScreen.FORGOT_PASSWORD
                    },
                    onCreateAccount = {
                        authViewModel.clearError()
                        currentScreen = AppScreen.SIGN_UP
                    },
                    isLoading = isLoading,
                    errorMessage = errorMessage
                )
            }

            /*
             * SIGN UP SCREEN
             */
            AppScreen.SIGN_UP -> {
                val isLoading = authState is AuthUiState.Loading
                val errorMessage = (authState as? AuthUiState.Error)?.message

                SignUpScreen(
                    onBack = {
                        authViewModel.clearError()
                        currentScreen = AppScreen.LOGIN
                    },
                    onCreateAccount = { fullName, pilotId, password, confirmPassword ->
                        authViewModel.clearError()
                        authViewModel.signUp(fullName, pilotId, password, confirmPassword)
                    },
                    isLoading = isLoading,
                    errorMessage = errorMessage
                )
            }

            /*
             * FORGOT PASSWORD SCREEN
             */
            AppScreen.FORGOT_PASSWORD -> {
                val isLoading = authState is AuthUiState.Loading
                val errorMessage = (authState as? AuthUiState.Error)?.message
                val successMessage = (authState as? AuthUiState.PasswordResetSuccess)?.message

                ForgotPasswordScreen(
                    onBack = {
                        authViewModel.clearError()
                        currentScreen = AppScreen.LOGIN
                    },
                    onResetPassword = { pilotId, newPassword, confirmNewPassword ->
                        authViewModel.clearError()
                        authViewModel.resetPassword(pilotId, newPassword, confirmNewPassword)
                    },
                    isLoading = isLoading,
                    errorMessage = errorMessage,
                    successMessage = successMessage
                )
            }

            /*
             * DASHBOARD SCREEN
             */
            AppScreen.DASHBOARD -> {
                DashboardScreen(
                    profile = activeProfile,
                    onMenuClick = { },
                    onProfileClick = { currentScreen = AppScreen.PROFILE },
                    onDetailsClick = { currentScreen = AppScreen.DETAILS },
                    onHistoryClick = { currentScreen = AppScreen.HISTORY },
                    onSettingsClick = { currentScreen = AppScreen.SETTINGS },
                    onLogoutClick = {
                        authViewModel.logout()
                        currentScreen = AppScreen.LOGIN
                    }
                )
            }

            /*
             * PROFILE SCREEN
             */
            AppScreen.PROFILE -> {
                ProfileScreen(
                    profile = activeProfile,
                    onBack = { currentScreen = AppScreen.DASHBOARD },
                    onSettingsClick = { currentScreen = AppScreen.SETTINGS },
                    onLogoutClick = {
                        authViewModel.logout()
                        currentScreen = AppScreen.LOGIN
                    }
                )
            }

            /*
             * DETAILS SCREEN
             */
            AppScreen.DETAILS -> {
                DetailsScreen(
                    profile = activeProfile,
                    onBack = { currentScreen = AppScreen.DASHBOARD }
                )
            }

            /*
             * HISTORY SCREEN
             */
            AppScreen.HISTORY -> {
                HistoryScreen(
                    pilotId = currentPilotId,
                    sessions = historyList,
                    onBack = { currentScreen = AppScreen.DASHBOARD }
                )
            }

            /*
             * SETTINGS SCREEN
             */
            AppScreen.SETTINGS -> {
                SettingsScreen(
                    profile = activeProfile,
                    onBack = { currentScreen = AppScreen.DASHBOARD },
                    onForgotPasswordClick = { currentScreen = AppScreen.FORGOT_PASSWORD },
                    onLogoutClick = {
                        authViewModel.logout()
                        currentScreen = AppScreen.LOGIN
                    }
                )
            }
        }
    }
}
