package com.aerovital.phone.ui.dashboard

import androidx.compose.runtime.Composable
import com.aerovital.phone.data.model.auth.PilotProfile
import com.aerovital.phone.ui.navigation.AppScreen
import com.aerovital.phone.ui.overview.OverviewScreen

/**
 * Main dashboard screen, delegating to the refreshed [OverviewScreen].
 * Preserves legacy parameter signatures for backward compatibility with existing tests and callers.
 */
@Composable
fun DashboardScreen(
    username: String? = null,
    pilot: PilotProfile?,
    latestHeartRate: Double? = null,
    onNavigate: (AppScreen) -> Unit,
    onLogoutClick: () -> Unit
) {
    OverviewScreen(
        username = username,
        pilot = pilot,
        latestHeartRate = latestHeartRate,
        watchConnected = true,
        isAcquisitionRunning = latestHeartRate != null,
        pendingQueueCount = 0,
        onNavigate = onNavigate
    )
}
