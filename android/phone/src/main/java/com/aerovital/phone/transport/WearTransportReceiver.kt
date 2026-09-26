package com.aerovital.phone.transport

import android.util.Log
import com.aerovital.phone.BuildConfig
import com.aerovital.shared.transport.ErrorReason
import com.aerovital.shared.transport.TransportEnvelope
import com.aerovital.shared.transport.TransportResult
import com.google.android.gms.wearable.MessageEvent
import com.google.android.gms.wearable.WearableListenerService
import com.google.gson.Gson
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.launch

class WearTransportReceiver : WearableListenerService() {
    private val gson = Gson()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onMessageReceived(messageEvent: MessageEvent) {
        super.onMessageReceived(messageEvent)

        if (messageEvent.path == MESSAGE_PATH) {
            val payloadString = String(messageEvent.data, Charsets.UTF_8)
            scope.launch {
                handleReceivedEnvelope(payloadString)
            }
        }
    }

    private suspend fun handleReceivedEnvelope(payloadString: String) {
        val result = validateAndParse(payloadString)
        when (result) {
            is TransportResult.Success -> {
                if (BuildConfig.DEBUG) {
                    Log.d(TAG, "Received valid envelope: ${result.data.messageId}")
                }
                _envelopeFlow.emit(result.data)
            }
            is TransportResult.Error -> {
                if (BuildConfig.DEBUG) {
                    Log.e(TAG, "Failed to parse/validate envelope: ${result.reason} - ${result.message}")
                }
                // Do not throw; gracefully discard malformed/invalid transport payloads
            }
        }
    }

    fun validateAndParse(payloadString: String): TransportResult<TransportEnvelope> {
        return try {
            val envelope = gson.fromJson(payloadString, TransportEnvelope::class.java)

            val validation = TransportEnvelope.validate(envelope, System.currentTimeMillis())
            if (validation is TransportResult.Error) {
                return validation
            }

            // Duplicate check
            if (!duplicateCache.addIfNotSeen(envelope.messageId)) {
                return TransportResult.Error(ErrorReason.DUPLICATE_MESSAGE, "Message ID already processed")
            }

            TransportResult.Success(envelope)
        } catch (e: Exception) {
            TransportResult.Error(ErrorReason.MALFORMED_ENVELOPE, e.message)
        }
    }

    companion object {
        const val TAG = "WearTransportReceiver"
        const val MESSAGE_PATH = "/aerovital/telemetry/v1"
        
        // Thread-safe bounded cache
        val duplicateCache = DuplicateMessageCache(maxCapacity = 1000)

        private val _envelopeFlow = MutableSharedFlow<TransportEnvelope>()
        val envelopeFlow: SharedFlow<TransportEnvelope> = _envelopeFlow
    }
}
