package com.aerovital.phone.ui.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Devices
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.MonitorHeart
import androidx.compose.material.icons.filled.Settings
import androidx.compose.ui.graphics.vector.ImageVector

/**
 * Top-level navigation destinations for the AeroVital Mobile Companion.
 */
enum class AppScreen(
    val title: String,
    val icon: ImageVector? = null,
    val isBottomNavDestination: Boolean = false
) {
    OVERVIEW("Overview", Icons.Default.Dashboard, true),
    MONITORING("Monitoring", Icons.Default.MonitorHeart, true),
    DEVICES("Devices", Icons.Default.Devices, true),
    HISTORY("History", Icons.Default.History, true),
    SETTINGS("Settings", Icons.Default.Settings, true),

    // Sub-destinations / Legacy alias support
    DASHBOARD("Overview", Icons.Default.Dashboard, false),
    DETAILS("Monitoring", Icons.Default.MonitorHeart, false),
    PROFILE("Profile", null, false),
    DIAGNOSTICS("Diagnostics", null, false);

    companion object {
        val bottomNavDestinations: List<AppScreen>
            get() = listOf(OVERVIEW, MONITORING, DEVICES, HISTORY, SETTINGS)
    }
}
