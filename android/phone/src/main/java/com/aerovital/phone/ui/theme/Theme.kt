package com.aerovital.phone.ui.theme

import android.app.Activity
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
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
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import androidx.core.view.WindowCompat

val LocalThemeIsDark = compositionLocalOf { false }

private val AeroVitalLightColors = lightColorScheme(
    primary = AeroLightPrimaryAction,
    onPrimary = AeroLightOnPrimary,
    primaryContainer = AeroLightSurfaceElevated,
    onPrimaryContainer = AeroLightTextPrimary,
    secondary = AeroFunctionalBlue,
    onSecondary = Color.White,
    tertiary = AeroLightTextSecondary,
    background = AeroLightCanvas,
    onBackground = AeroLightTextPrimary,
    surface = AeroLightSurface,
    onSurface = AeroLightTextPrimary,
    surfaceVariant = AeroLightSurfaceElevated,
    onSurfaceVariant = AeroLightTextSecondary,
    outline = AeroLightBorder,
    outlineVariant = AeroLightBorderStrong,
    error = AeroSemanticRed,
    onError = Color.White
)

private val AeroVitalDarkColors = darkColorScheme(
    primary = AeroDarkPrimaryAction,
    onPrimary = AeroDarkOnPrimary,
    primaryContainer = AeroDarkSurfaceElevated,
    onPrimaryContainer = AeroDarkTextPrimary,
    secondary = AeroDarkFunctionalBlue,
    onSecondary = AeroDarkCanvas,
    tertiary = AeroDarkTextSecondary,
    background = AeroDarkCanvas,
    onBackground = AeroDarkTextPrimary,
    surface = AeroDarkSurface,
    onSurface = AeroDarkTextPrimary,
    surfaceVariant = AeroDarkSurfaceElevated,
    onSurfaceVariant = AeroDarkTextSecondary,
    outline = AeroDarkBorder,
    outlineVariant = AeroDarkBorderStrong,
    error = AeroSemanticRedDark,
    onError = Color.White
)

val AeroVitalTypography = Typography(
    headlineLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 28.sp,
        lineHeight = 34.sp,
        letterSpacing = (-0.5).sp
    ),
    headlineMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 22.sp,
        lineHeight = 28.sp,
        letterSpacing = (-0.2).sp
    ),
    titleLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 18.sp,
        lineHeight = 24.sp,
        letterSpacing = 0.sp
    ),
    titleMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Medium,
        fontSize = 15.sp,
        lineHeight = 20.sp,
        letterSpacing = 0.1.sp
    ),
    bodyLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 14.sp,
        lineHeight = 20.sp,
        letterSpacing = 0.2.sp
    ),
    bodyMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 13.sp,
        lineHeight = 18.sp,
        letterSpacing = 0.2.sp
    ),
    labelSmall = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Medium,
        fontSize = 11.sp,
        lineHeight = 14.sp,
        letterSpacing = 0.5.sp
    )
)

@Composable
fun AeroVitalTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) AeroVitalDarkColors else AeroVitalLightColors
    val view = LocalView.current

    if (!view.isInEditMode) {
        SideEffect {
            val activity = view.context as? ComponentActivity
            val window = activity?.window ?: (view.context as? Activity)?.window
            if (window != null) {
                val bg = if (darkTheme) AeroDarkCanvas else AeroLightCanvas
                window.statusBarColor = bg.toArgb()
                window.navigationBarColor = bg.toArgb()
                val insetsController = WindowCompat.getInsetsController(window, view)
                insetsController.isAppearanceLightStatusBars = !darkTheme
                insetsController.isAppearanceLightNavigationBars = !darkTheme
            }
            if (activity != null) {
                val statusColor = if (darkTheme) AeroDarkCanvas.toArgb() else AeroLightCanvas.toArgb()
                val navColor = if (darkTheme) AeroDarkCanvas.toArgb() else AeroLightCanvas.toArgb()
                val statusStyle = if (darkTheme) {
                    SystemBarStyle.dark(statusColor)
                } else {
                    SystemBarStyle.light(statusColor, AeroLightPrimaryAction.toArgb())
                }
                val navStyle = if (darkTheme) {
                    SystemBarStyle.dark(navColor)
                } else {
                    SystemBarStyle.light(navColor, AeroLightPrimaryAction.toArgb())
                }
                activity.enableEdgeToEdge(statusStyle, navStyle)
            }
        }
    }

    CompositionLocalProvider(LocalThemeIsDark provides darkTheme) {
        MaterialTheme(
            colorScheme = colorScheme,
            typography = AeroVitalTypography,
            content = content
        )
    }
}
