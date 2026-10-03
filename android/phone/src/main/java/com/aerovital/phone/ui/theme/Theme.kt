package com.aerovital.phone.ui.theme

import android.app.Activity
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.enableEdgeToEdge
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

val LocalThemeIsDark = compositionLocalOf { false }

private val AeroVitalColors = lightColorScheme(
    // Main colors
    primary = AeroNavy,
    onPrimary = AeroSurface,

    // Primary container
    primaryContainer = AeroLightBlue,
    onPrimaryContainer = AeroDarkNavy,

    // Secondary colors
    secondary = AeroBlue,
    onSecondary = AeroSurface,

    // Background
    background = AeroBackground,
    onBackground = AeroText,

    // Surface / cards
    surface = AeroSurface,
    onSurface = AeroText,

    // Alternative surface
    surfaceVariant = AeroLightBlue,
    onSurfaceVariant = AeroDarkNavy
)

private val AeroVitalDarkColors = darkColorScheme(
    // Main colors
    primary = AeroDarkPrimary,
    onPrimary = AeroDarkNavy,

    // Primary container
    primaryContainer = AeroDarkPrimaryContainer,
    onPrimaryContainer = AeroDarkOnPrimaryContainer,

    // Secondary colors
    secondary = AeroDarkSecondary,
    onSecondary = AeroDarkNavy,

    // Background
    background = AeroDarkBackground,
    onBackground = AeroDarkText,

    // Surface / cards
    surface = AeroDarkSurface,
    onSurface = AeroDarkText,

    // Alternative surface
    surfaceVariant = AeroDarkSurfaceVariant,
    onSurfaceVariant = AeroDarkSubtext,

    outline = AeroDarkOutline,
    outlineVariant = AeroDarkOutlineVariant,
    error = Color(0xFFEF5350),
    onError = Color(0xFFFFFFFF)
)

@Composable
fun AeroVitalTheme(
    darkTheme: Boolean = false,
    content: @Composable () -> Unit
) {
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val activity = view.context as? ComponentActivity
            val window = activity?.window ?: (view.context as? Activity)?.window
            if (window != null) {
                val bg = if (darkTheme) AeroDarkBackground else AeroBackground
                window.statusBarColor = bg.toArgb()
                window.navigationBarColor = bg.toArgb()
                val insetsController = WindowCompat.getInsetsController(window, view)
                insetsController.isAppearanceLightStatusBars = !darkTheme
                insetsController.isAppearanceLightNavigationBars = !darkTheme
            }
            if (activity != null) {
                val statusColor = if (darkTheme) AeroDarkBackground.toArgb() else AeroBackground.toArgb()
                val navColor = if (darkTheme) AeroDarkBackground.toArgb() else AeroBackground.toArgb()
                val statusStyle = if (darkTheme) {
                    SystemBarStyle.dark(statusColor)
                } else {
                    SystemBarStyle.light(statusColor, AeroDarkNavy.toArgb())
                }
                val navStyle = if (darkTheme) {
                    SystemBarStyle.dark(navColor)
                } else {
                    SystemBarStyle.light(navColor, AeroDarkNavy.toArgb())
                }
                activity.enableEdgeToEdge(statusStyle, navStyle)
            }
        }
    }

    CompositionLocalProvider(LocalThemeIsDark provides darkTheme) {
        MaterialTheme(
            colorScheme = if (darkTheme) AeroVitalDarkColors else AeroVitalColors,
            typography = Typography(),
            content = content
        )
    }
}
