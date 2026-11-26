package com.aerovital.phone.ui.theme

import android.content.Context

/**
 * Manages user appearance preferences for AeroVital phone application.
 *
 * Supports:
 * - SYSTEM: Automatically follows the Android OS system dark/light configuration.
 * - LIGHT: Crisp aviation clinical daytime HUD.
 * - DARK: Night glass-cockpit high-contrast navy HUD.
 *
 * Fully preserves backward compatibility for existing boolean [isDarkMode] APIs.
 */
enum class ThemeMode {
    SYSTEM,
    LIGHT,
    DARK
}

object ThemePreferences {
    private const val PREFS_NAME = "aerovital_theme_preferences"
    private const val KEY_THEME_MODE = "theme_mode_enum"
    private const val KEY_DARK_MODE = "dark_mode_enabled"

    /**
     * Returns the selected [ThemeMode] (defaults to SYSTEM).
     */
    fun getThemeMode(context: Context): ThemeMode {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val modeStr = prefs.getString(KEY_THEME_MODE, null)
        if (modeStr != null) {
            return try {
                ThemeMode.valueOf(modeStr)
            } catch (e: Exception) {
                ThemeMode.SYSTEM
            }
        }
        // Legacy fallback
        val legacyDark = prefs.getBoolean(KEY_DARK_MODE, false)
        return if (legacyDark) ThemeMode.DARK else ThemeMode.SYSTEM
    }

    /**
     * Persists the user's [ThemeMode] preference.
     */
    fun setThemeMode(context: Context, mode: ThemeMode) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_THEME_MODE, mode.name)
            .putBoolean(KEY_DARK_MODE, mode == ThemeMode.DARK)
            .apply()
    }

    /**
     * Legacy helper: returns true if dark mode is explicitly forced or active.
     */
    fun isDarkMode(context: Context): Boolean {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val mode = getThemeMode(context)
        return when (mode) {
            ThemeMode.DARK -> true
            ThemeMode.LIGHT -> false
            ThemeMode.SYSTEM -> prefs.getBoolean(KEY_DARK_MODE, false)
        }
    }

    /**
     * Legacy helper: sets dark mode explicitly (maps true -> DARK, false -> LIGHT).
     */
    fun setDarkMode(context: Context, enabled: Boolean) {
        setThemeMode(context, if (enabled) ThemeMode.DARK else ThemeMode.LIGHT)
    }
}
