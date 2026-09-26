package com.aerovital.phone.telemetry

import android.util.Log
import com.aerovital.phone.BuildConfig
import com.aerovital.phone.data.remote.DjangoTelemetryClient
import com.aerovital.phone.data.remote.TelemetryIngestResult
import com.aerovital.phone.transport.WearTransportReceiver
import com.aerovital.shared.telemetry.toCanonicalTelemetry
import com.aerovital.shared.transport.TransportEnvelope
import com.aerovital.shared.transport.TransportResult

/**
 * Phone-side telemetry ingestion coordinator.
 *
 * Integrates the existing WearTransportReceiver with the A5 Django telemetry client.
 *
 * Enforces the flow:
 * TransportEnvelope received
 *        ↓
 * Existing envelope validation (WearTransportReceiver.validateAndParse)
 *        ↓
 * CanonicalTelemetry extraction (envelope.toCanonicalTelemetry())
 *        ↓
 * A5 Django telemetry client (telemetryClient.sendTelemetry(telemetry))
 *        ↓
 * HTTP request (POST /api/v1/telemetry/)
 *        ↓
 * Explicit result (TelemetryIngestResult)
 */
class PhoneTelemetryIngestionHandler(
    private val telemetryClient: DjangoTelemetryClient,
    private val receiver: WearTransportReceiver = WearTransportReceiver()
) {
    /**
     * Ingests a validated TransportEnvelope:
     * 1. Confirms payloadType is PHYSIOLOGICAL_TELEMETRY
     * 2. Extracts CanonicalTelemetry using the canonical mapper
     * 3. Dispatches to Django telemetry client
     */
    suspend fun handleEnvelope(envelope: TransportEnvelope): TelemetryIngestResult {
        if (envelope.payloadType != TransportEnvelope.PAYLOAD_TYPE_TELEMETRY) {
            return TelemetryIngestResult.MalformedPayloadError(
                "Envelope payloadType '${envelope.payloadType}' does not match expected '${TransportEnvelope.PAYLOAD_TYPE_TELEMETRY}'"
            )
        }

        val telemetry = envelope.toCanonicalTelemetry()
            ?: return TelemetryIngestResult.MalformedPayloadError(
                "Failed to deserialize CanonicalTelemetry from envelope payload (messageId=${envelope.messageId})"
            )

        if (telemetry.timestamp.isBlank()) {
            return TelemetryIngestResult.MalformedPayloadError(
                "CanonicalTelemetry timestamp cannot be blank (messageId=${envelope.messageId})"
            )
        }

        if (BuildConfig.DEBUG) {
            Log.d(TAG, "Forwarding telemetry for messageId=${envelope.messageId} to Django backend")
        }

        val result = telemetryClient.sendTelemetry(telemetry)

        if (BuildConfig.DEBUG) {
            when (result) {
                is TelemetryIngestResult.Success -> {
                    Log.d(TAG, "Telemetry ingested successfully: messageId=${envelope.messageId}, status=${result.statusCode}")
                }
                else -> {
                    Log.w(TAG, "Telemetry ingestion failed: messageId=${envelope.messageId}, result=$result")
                }
            }
        }

        return result
    }

    /**
     * Ingests a raw transport payload string through existing envelope validation,
     * extracts CanonicalTelemetry, and sends it to Django.
     */
    suspend fun handlePayloadString(payloadString: String): TelemetryIngestResult {
        return when (val validationResult = receiver.validateAndParse(payloadString)) {
            is TransportResult.Success -> handleEnvelope(validationResult.data)
            is TransportResult.Error -> TelemetryIngestResult.MalformedPayloadError(
                "Envelope validation failed: [${validationResult.reason}] ${validationResult.message}"
            )
        }
    }

    companion object {
        private const val TAG = "PhoneTelemetryHandler"
    }
}
