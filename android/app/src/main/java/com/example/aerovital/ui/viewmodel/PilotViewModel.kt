package com.example.aerovital.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.aerovital.data.model.FlightSession
import com.example.aerovital.data.model.PilotProfile
import com.example.aerovital.data.repository.PilotRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

sealed class PilotUiState {
    object Loading : PilotUiState()
    data class Success(
        val profile: PilotProfile,
        val history: List<FlightSession>
    ) : PilotUiState()
    data class Error(val message: String) : PilotUiState()
}

class PilotViewModel(
    private val pilotRepository: PilotRepository = PilotRepository()
) : ViewModel() {

    private val _pilotState = MutableStateFlow<PilotUiState>(PilotUiState.Loading)
    val pilotState: StateFlow<PilotUiState> = _pilotState

    fun loadPilotData(pilotId: String) {
        _pilotState.value = PilotUiState.Loading

        viewModelScope.launch {
            val profile = pilotRepository.getPilotProfile(pilotId)
            if (profile != null) {
                val history = pilotRepository.getFlightHistory(pilotId)
                _pilotState.value = PilotUiState.Success(
                    profile = profile,
                    history = history
                )
            } else {
                _pilotState.value = PilotUiState.Error("Failed to load profile for $pilotId.")
            }
        }
    }
}
