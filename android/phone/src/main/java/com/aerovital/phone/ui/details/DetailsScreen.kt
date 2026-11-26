package com.aerovital.phone.ui.details

import androidx.compose.runtime.Composable
import com.aerovital.phone.data.model.auth.PilotProfile
import com.aerovital.phone.ui.monitoring.MonitoringScreen

/**
 * Details screen, delegating to the refreshed [MonitoringScreen].
 * Preserves legacy parameter signatures for backward compatibility with existing tests and callers.
 */
@Composable
fun DetailsScreen(
    username: String? = null,
    pilot: PilotProfile?,
    latestHeartRate: Double? = null,
    onBack: () -> Unit,
    onDiagnosticsClick: () -> Unit
) {
    MonitoringScreen(
        username = username,
        pilot = pilot,
        latestHeartRate = latestHeartRate,
        onNavigateBack = onBack
    )
}
