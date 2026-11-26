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
 * Repository providing latest verified telemetry observations and historical sortie telemetry
 * from the Django REST backend.
 */
class TelemetryRepository(
    private val telemetryApiProvider: () -> TelemetryApi,
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.IO)
) {
    // Secondary constructor for backward compatibility with unit tests
    constructor(telemetryApi: TelemetryApi, scope: CoroutineScope = CoroutineScope(Dispatchers.IO)) : this({ telemetryApi }, scope)

    private val telemetryApi: TelemetryApi get() = telemetryApiProvider()

    private val _latestTelemetry = MutableStateFlow<TelemetryDto?>(null)
    val latestTelemetry: StateFlow<TelemetryDto?> = _latestTelemetry.asStateFlow()

    private val _telemetryHistory = MutableStateFlow<List<TelemetryDto>>(emptyList())
    val telemetryHistory: StateFlow<List<TelemetryDto>> = _telemetryHistory.asStateFlow()

    private val _historyLoading = MutableStateFlow(false)
    val historyLoading: StateFlow<Boolean> = _historyLoading.asStateFlow()

    private val _historyError = MutableStateFlow<String?>(null)
    val historyError: StateFlow<String?> = _historyError.asStateFlow()

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

    suspend fun fetchHistory() {
        _historyLoading.value = true
        _historyError.value = null
        try {
            val response = telemetryApi.getTelemetry(limit = 20, hasHr = null)
            if (response.isSuccessful) {
                _telemetryHistory.value = response.body() ?: emptyList()
            } else {
                _historyError.value = "Backend returned HTTP ${response.code()}"
            }
        } catch (e: Exception) {
            Log.w("TelemetryRepository", "Failed fetching telemetry history: ${e.message}")
            _historyError.value = e.message ?: "Failed connecting to backend"
        } finally {
            _historyLoading.value = false
        }
    }
}
