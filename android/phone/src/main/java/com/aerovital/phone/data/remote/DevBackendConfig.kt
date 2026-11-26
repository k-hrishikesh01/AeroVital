package com.aerovital.phone.data.remote

import android.content.Context
import android.util.Log
import com.aerovital.phone.BuildConfig

/**
 * Manages centrally configured backend endpoints for standalone production operation
 * and development-time testing.
 *
 * Production Base URL:
 * - https://aerovital-api.onrender.com/ (AeroVital Deployed Django REST API)
 *
 * Optional Local Development Overrides:
 * - Physical Phone via ADB Reverse: http://127.0.0.1:8000/
 * - Android Emulator: http://10.0.2.2:8000/
 */
object DevBackendConfig {
    private const val TAG = "DevBackendConfig"
    private const val PREFS_NAME = "aerovital_dev_config"
    private const val KEY_BASE_URL = "backend_base_url"

    const val PRODUCTION_API_URL = "https://aerovital-api.onrender.com/"
    const val DEFAULT_EMULATOR_URL = "http://10.0.2.2:8000/"
    const val DEFAULT_ADB_REVERSE_URL = "http://127.0.0.1:8000/"

    /**
     * Initializes ApiClient.BASE_URL from persistent storage on application startup.
     * Defaults to the production deployed Django REST API.
     */
    fun init(context: Context) {
        val configuredUrl = getBaseUrl(context)
        ApiClient.BASE_URL = configuredUrl
        if (BuildConfig.DEBUG) {
            Log.d(TAG, "Initialized backend BASE_URL: $configuredUrl")
        }
    }

    /**
     * Retrieves the currently configured backend base URL, defaulting to production.
     */
    fun getBaseUrl(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        return prefs.getString(KEY_BASE_URL, PRODUCTION_API_URL) ?: PRODUCTION_API_URL
    }

    /**
     * Updates and persists the backend base URL, instantly updating ApiClient.
     */
    fun setBaseUrl(context: Context, url: String) {
        val normalized = normalizeUrl(url)
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_BASE_URL, normalized)
            .apply()
        ApiClient.BASE_URL = normalized
        if (BuildConfig.DEBUG) {
            Log.d(TAG, "Updated backend BASE_URL: $normalized")
        }
    }

    /**
     * Resets the configuration to the production API base URL.
     */
    fun resetToDefault(context: Context) {
        setBaseUrl(context, PRODUCTION_API_URL)
    }

    /**
     * Ensures the URL ends with a trailing slash as required by Retrofit.
     */
    fun normalizeUrl(url: String): String {
        val trimmed = url.trim()
        return if (!trimmed.endsWith("/")) "$trimmed/" else trimmed
    }
}
