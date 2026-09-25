package com.example.aerovital.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable


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


@Composable
fun AeroVitalTheme(
    content: @Composable () -> Unit
) {

    MaterialTheme(
        colorScheme = AeroVitalColors,
        typography = Typography,
        content = content
    )
}