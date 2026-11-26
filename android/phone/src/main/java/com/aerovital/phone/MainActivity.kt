package com.aerovital.phone

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.aerovital.phone.data.remote.ApiClient
import com.aerovital.phone.data.remote.DevBackendConfig
import com.aerovital.phone.data.remote.SecureTokenManager
import com.aerovital.phone.data.remote.TokenManager
import com.aerovital.phone.data.repository.AuthRepository
import com.aerovital.phone.data.repository.AuthState
import com.aerovital.phone.data.repository.TelemetryRepository
import com.aerovital.phone.transport.WearTransportReceiver
import com.aerovital.phone.ui.auth.AuthViewModel
import com.aerovital.phone.ui.auth.LoginScreen
import com.aerovital.phone.ui.devices.DevicesScreen
import com.aerovital.phone.ui.diagnostic.PhoneDiagnosticScreen
import com.aerovital.phone.ui.history.HistoryScreen
import com.aerovital.phone.ui.monitoring.MonitoringScreen
import com.aerovital.phone.ui.navigation.AppScreen
import com.aerovital.phone.ui.overview.OverviewScreen
import com.aerovital.phone.ui.profile.ProfileScreen
import com.aerovital.phone.ui.settings.SettingsScreen
import com.aerovital.phone.ui.theme.*

class MainActivity : ComponentActivity() {

    private lateinit var authRepository: AuthRepository
    private lateinit var tokenManager: TokenManager
    private lateinit var telemetryRepository: TelemetryRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Initialize development backend configuration
        DevBackendConfig.init(applicationContext)

        // Ensure background transport receiver handler is eagerly prepared
        WearTransportReceiver.getOrInitHandler(applicationContext)

        tokenManager = SecureTokenManager(applicationContext)
        authRepository = AuthRepository(
            authApiProvider = {
                ApiClient.getAuthApi(applicationContext) {
                    authRepository.handleUnauthorized()
                }
            },
            tokenManager = tokenManager
        )
        telemetryRepository = TelemetryRepository(
            telemetryApiProvider = {
                ApiClient.getTelemetryApi(applicationContext)
            }
        )

        setContent {
            val context = LocalContext.current
            var currentThemeMode by rememberSaveable { mutableStateOf(ThemePreferences.getThemeMode(context)) }
            val systemDark = isSystemInDarkTheme()
            val effectiveDark = when (currentThemeMode) {
                ThemeMode.SYSTEM -> systemDark
                ThemeMode.LIGHT -> false
                ThemeMode.DARK -> true
            }

            AeroVitalTheme(darkTheme = effectiveDark) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val authViewModel: AuthViewModel = viewModel(
                        factory = AuthViewModel.Factory(authRepository)
                    )

                    val authState by authViewModel.authState.collectAsStateWithLifecycle()
                    val latestTelemetryDto by telemetryRepository.latestTelemetry.collectAsStateWithLifecycle()
                    val latestHeartRate = latestTelemetryDto?.heartRate

                    var currentScreen by rememberSaveable { mutableStateOf(AppScreen.OVERVIEW) }
                    var isAcquisitionRunning by rememberSaveable { mutableStateOf(false) }

                    when (authState) {
                        is AuthState.Authenticated -> {
                            val auth = authState as AuthState.Authenticated

                            if (currentScreen != AppScreen.OVERVIEW) {
                                BackHandler {
                                    currentScreen = AppScreen.OVERVIEW
                                }
                            }

                            Scaffold(
                                bottomBar = {
                                    NavigationBar(
                                        containerColor = MaterialTheme.colorScheme.surface,
                                        contentColor = MaterialTheme.colorScheme.onSurface
                                    ) {
                                        AppScreen.bottomNavDestinations.forEach { screen ->
                                            val isSelected = currentScreen == screen ||
                                                    (screen == AppScreen.OVERVIEW && currentScreen == AppScreen.DASHBOARD) ||
                                                    (screen == AppScreen.MONITORING && currentScreen == AppScreen.DETAILS)
                                            NavigationBarItem(
                                                selected = isSelected,
                                                onClick = { currentScreen = screen },
                                                icon = {
                                                    screen.icon?.let { icon ->
                                                        Icon(
                                                            imageVector = icon,
                                                            contentDescription = screen.title
                                                        )
                                                    }
                                                },
                                                label = {
                                                    Text(
                                                        text = screen.title,
                                                        style = MaterialTheme.typography.labelSmall
                                                    )
                                                },
                                                colors = NavigationBarItemDefaults.colors(
                                                    selectedIconColor = MaterialTheme.colorScheme.primary,
                                                    selectedTextColor = MaterialTheme.colorScheme.primary,
                                                    indicatorColor = MaterialTheme.colorScheme.primaryContainer
                                                )
                                            )
                                        }
                                    }
                                }
                            ) { innerPadding ->
                                when (currentScreen) {
                                    AppScreen.OVERVIEW, AppScreen.DASHBOARD -> {
                                        OverviewScreen(
                                            username = auth.username,
                                            pilot = auth.pilot,
                                            latestHeartRate = latestHeartRate,
                                            watchConnected = true,
                                            isAcquisitionRunning = isAcquisitionRunning,
                                            pendingQueueCount = 0,
                                            onNavigate = { destination -> currentScreen = destination },
                                            onToggleAcquisition = { isAcquisitionRunning = !isAcquisitionRunning }
                                        )
                                    }
                                    AppScreen.MONITORING, AppScreen.DETAILS -> {
                                        MonitoringScreen(
                                            username = auth.username,
                                            pilot = auth.pilot,
                                            latestHeartRate = latestHeartRate,
                                            accelX = 0.02f,
                                            accelY = 0.98f,
                                            accelZ = 0.15f,
                                            onNavigateBack = { currentScreen = AppScreen.OVERVIEW }
                                        )
                                    }
                                    AppScreen.DEVICES -> {
                                        DevicesScreen(
                                            watchConnected = true,
                                            isAcquisitionRunning = isAcquisitionRunning,
                                            watchBatteryLevel = 84,
                                            totalObservationsReceived = 2450L,
                                            onToggleAcquisition = { isAcquisitionRunning = !isAcquisitionRunning }
                                        )
                                    }
                                    AppScreen.HISTORY -> {
                                        HistoryScreen(
                                            pilotCode = auth.pilot?.pilotCode ?: "PL-01",
                                            telemetryRepository = telemetryRepository,
                                            onBack = { currentScreen = AppScreen.OVERVIEW }
                                        )
                                    }
                                    AppScreen.SETTINGS, AppScreen.PROFILE -> {
                                        SettingsScreen(
                                            username = auth.username,
                                            pilot = auth.pilot,
                                            currentThemeMode = currentThemeMode,
                                            onThemeModeChanged = { mode ->
                                                currentThemeMode = mode
                                                ThemePreferences.setThemeMode(context, mode)
                                            },
                                            isDarkMode = effectiveDark,
                                            onDarkModeChanged = { enabled ->
                                                currentThemeMode = if (enabled) ThemeMode.DARK else ThemeMode.LIGHT
                                                ThemePreferences.setThemeMode(context, currentThemeMode)
                                            },
                                            onBack = { currentScreen = AppScreen.OVERVIEW },
                                            onDiagnosticsClick = { currentScreen = AppScreen.DIAGNOSTICS },
                                            onLogoutClick = {
                                                authViewModel.logout()
                                                currentScreen = AppScreen.OVERVIEW
                                            }
                                        )
                                    }
                                    AppScreen.DIAGNOSTICS -> {
                                        PhoneDiagnosticScreen(
                                            username = auth.username,
                                            pilot = auth.pilot,
                                            onLogout = {
                                                authViewModel.logout()
                                                currentScreen = AppScreen.OVERVIEW
                                            },
                                            onBack = { currentScreen = AppScreen.OVERVIEW }
                                        )
                                    }
                                }
                            }
                        }
                        else -> {
                            LoginScreen(
                                viewModel = authViewModel,
                                onLoginSuccess = {
                                    currentScreen = AppScreen.OVERVIEW
                                }
                            )
                        }
                    }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        if (::telemetryRepository.isInitialized) {
            telemetryRepository.startPolling()
        }
    }

    override fun onPause() {
        super.onPause()
        if (::telemetryRepository.isInitialized) {
            telemetryRepository.stopPolling()
        }
    }
}
