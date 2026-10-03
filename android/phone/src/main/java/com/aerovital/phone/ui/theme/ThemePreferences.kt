package com.aerovital.phone.ui.theme

import android.content.Context

/**
 * Manages user appearance preferences for AeroVital phone application.
 *
 * Persists user-selected Light / Dark mode authoritative choice across
 * navigation, configuration changes, and app restarts via lightweight
 * SharedPreferences storage.
 */
object ThemePreferences {
    private const val PREFS_NAME = "aerovital_theme_preferences"
    private const val KEY_DARK_MODE = "dark_mode_enabled"

    /**
     * Returns true if the user explicitly enabled dark mode, false otherwise (defaults to Light).
     */
    fun isDarkMode(context: Context): Boolean {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return prefs.getBoolean(KEY_DARK_MODE, false)
    }

    /**
     * Persists user choice for dark mode.
     */
    fun setDarkMode(context: Context, enabled: Boolean) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putBoolean(KEY_DARK_MODE, enabled)
            .apply()
    }
}
