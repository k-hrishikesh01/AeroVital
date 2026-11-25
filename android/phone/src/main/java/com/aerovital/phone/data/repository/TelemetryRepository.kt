package com.aerovital.phone.data.repository

import android.util.Log
import com.aerovital.phone.data.model.telemetry.TelemetryDto
import com.aerovital.phone.data.remote.TelemetryApi
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * Repository providing latest verified telemetry observations from Django backend.
 */
class TelemetryRepository(
    private val telemetryApi: TelemetryApi,
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.IO)
) {
    private val _latestTelemetry = MutableStateFlow<TelemetryDto?>(null)
    val latestTelemetry: StateFlow<TelemetryDto?> = _latestTelemetry.asStateFlow()

    private var pollingJob: Job? = null

    fun startPolling(intervalMs: Long = 3000L) {
        if (pollingJob?.isActive == true) return
        pollingJob = scope.launch {
            while (isActive) {
                fetchLatestTelemetry()
                delay(intervalMs)
            }
        }
    }

    fun stopPolling() {
        pollingJob?.cancel()
        pollingJob = null
    }

    suspend fun fetchLatestTelemetry(): TelemetryDto? {
        return try {
            val response = telemetryApi.getTelemetry(limit = 5, hasHr = true)
            if (response.isSuccessful) {
                val list = response.body()
                val latest = list?.firstOrNull { it.heartRate != null } ?: list?.firstOrNull()
                if (latest != null) {
                    _latestTelemetry.value = latest
                }
                latest
            } else {
                null
            }
        } catch (e: Exception) {
            Log.w("TelemetryRepository", "Failed fetching telemetry from backend: ${e.message}")
            null
        }
    }
}
