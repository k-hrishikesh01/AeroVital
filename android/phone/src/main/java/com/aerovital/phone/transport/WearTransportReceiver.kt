package com.aerovital.phone.transport

import android.content.Context
import android.util.Log
import com.aerovital.phone.BuildConfig
import com.aerovital.phone.data.remote.ApiClient
import com.aerovital.shared.transport.ErrorReason
import com.aerovital.shared.transport.TelemetryAck
import com.aerovital.shared.transport.TransportEnvelope
import com.aerovital.shared.transport.TransportResult
import com.google.android.gms.wearable.MessageEvent
import com.google.android.gms.wearable.WearableListenerService
import com.google.gson.Gson
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

import com.aerovital.phone.telemetry.PhoneTelemetryIngestionHandler

/**
 * Diagnostic state tracking for transport message arrival.
 */
data class TransportDiagnosticState(
    val totalReceivedEnvelopes: Long = 0L,
    val lastReceivedMessageId: String? = null,
    val lastReceivedDeviceId: String? = null,
    val lastReceivedTimestampEpochMs: Long? = null,
    val lastError: String? = null
)

class WearTransportReceiver : WearableListenerService() {
    private val gson = Gson()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onMessageReceived(messageEvent: MessageEvent) {
        super.onMessageReceived(messageEvent)

        if (messageEvent.path == MESSAGE_PATH) {
            val payloadString = String(messageEvent.data, Charsets.UTF_8)
            val sourceNodeId = messageEvent.sourceNodeId
            scope.launch {
                handleReceivedEnvelope(payloadString, sourceNodeId)
            }
        }
    }

    internal suspend fun handleReceivedEnvelope(payloadString: String, sourceNodeId: String? = null) {
        val result = validateAndParse(payloadString)
        when (result) {
            is TransportResult.Success -> {
                if (BuildConfig.DEBUG) {
                    Log.d(TAG, "Received valid envelope: ${result.data.messageId}")
                }
                _envelopeFlow.emit(result.data)
                _diagnosticState.update { current ->
                    current.copy(
                        totalReceivedEnvelopes = current.totalReceivedEnvelopes + 1,
                        lastReceivedMessageId = result.data.messageId,
                        lastReceivedDeviceId = result.data.deviceId,
                        lastReceivedTimestampEpochMs = result.data.timestamp
                    )
                }
                val handler = telemetryHandler ?: try {
                    getOrInitHandler(applicationContext)
                } catch (e: Throwable) {
                    null
                }
                val ingestResult = handler?.handleEnvelope(result.data)

                // Dispatch application-level durable confirmation ACK back to the watch
                if (sourceNodeId != null && ingestResult !is com.aerovital.phone.data.remote.TelemetryIngestResult.MalformedPayloadError) {
                    val ack = TelemetryAck(
                        messageId = result.data.messageId,
                        batchId = result.data.batchId,
                        sequenceNumber = result.data.sequenceNumber,
                        status = TelemetryAck.STATUS_STORED
                    )
                    resolveAckSender()?.sendAck(sourceNodeId, ack)
                }
            }
            is TransportResult.Error -> {
                if (BuildConfig.DEBUG) {
                    Log.e(TAG, "Failed to parse/validate envelope: ${result.reason} - ${result.message}")
                }
                _diagnosticState.update { current ->
                    current.copy(lastError = "${result.reason}: ${result.message}")
                }
                // If message was a duplicate, send DUPLICATE ACK so watch can safely evict it from buffer
                if (result.reason == ErrorReason.DUPLICATE_MESSAGE && sourceNodeId != null) {
                    try {
                        val parsed = gson.fromJson(payloadString, TransportEnvelope::class.java)
                        val duplicateAck = TelemetryAck(
                            messageId = parsed.messageId,
                            batchId = parsed.batchId,
                            sequenceNumber = parsed.sequenceNumber,
                            status = TelemetryAck.STATUS_DUPLICATE
                        )
                        resolveAckSender()?.sendAck(sourceNodeId, duplicateAck)
                    } catch (ignored: Exception) {}
                }
            }
        }
    }

    private fun resolveAckSender(): PhoneAckSender? {
        val custom = customAckSender
        if (custom != null) return custom
        return try {
            DefaultPhoneAckSender(applicationContext)
        } catch (e: Throwable) {
            null
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

        @Volatile
        var customAckSender: PhoneAckSender? = null

        private val _envelopeFlow = MutableSharedFlow<TransportEnvelope>()
        val envelopeFlow: SharedFlow<TransportEnvelope> = _envelopeFlow

        private val _diagnosticState = MutableStateFlow(TransportDiagnosticState())
        val diagnosticState: StateFlow<TransportDiagnosticState> = _diagnosticState

        /**
         * Telemetry ingestion handler for forwarding valid envelopes to Django backend.
         * If null, [getOrInitHandler] lazily constructs a persistent instance.
         */
        @Volatile
        var telemetryHandler: PhoneTelemetryIngestionHandler? = null

        /**
         * Resolves or lazily constructs the application-level PhoneTelemetryIngestionHandler
         * using existing A5/A6 components so background service dispatch succeeds even if
         * MainActivity has never run.
         */
        fun getOrInitHandler(context: Context): PhoneTelemetryIngestionHandler {
            val existing = telemetryHandler
            if (existing != null) return existing
            return synchronized(this) {
                telemetryHandler ?: run {
                    val appContext = context.applicationContext
                    val client = ApiClient.getTelemetryClient(appContext)
                    val handler = PhoneTelemetryIngestionHandler.create(
                        context = appContext,
                        telemetryClient = client
                    )
                    telemetryHandler = handler
                    handler
                }
            }
        }
    }
}
