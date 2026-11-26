package com.aerovital.phone.telemetry

import android.content.Context
import android.util.Log
import com.aerovital.phone.BuildConfig
import com.aerovital.phone.data.remote.DjangoTelemetryClient
import com.aerovital.phone.data.remote.TelemetryIngestResult
import com.aerovital.phone.queue.DurableTelemetryQueueStore
import com.aerovital.phone.queue.EnqueueResult
import com.aerovital.phone.queue.QueueRetryPolicy
import com.aerovital.phone.queue.TelemetryDeliveryCoordinator
import com.aerovital.phone.queue.TelemetryQueue
import com.aerovital.phone.transport.WearTransportReceiver
import com.aerovital.shared.telemetry.toCanonicalTelemetry
import com.aerovital.shared.transport.TelemetryBatch
import com.aerovital.shared.transport.TransportEnvelope
import com.aerovital.shared.transport.TransportResult

/**
 * Phone-side telemetry ingestion coordinator with durable store-and-forward queuing.
 *
 * Enforces the Milestone A6 flow:
 * Watch
 *   ↓
 * TransportEnvelope received
 *   ↓
 * Envelope validation (WearTransportReceiver.validateAndParse)
 *   ↓
 * CanonicalTelemetry extraction & validation (envelope.toCanonicalTelemetry())
 *   ↓
 * Durable local queue (TelemetryQueue.enqueue)
 *   ↓
 * Delivery worker (TelemetryDeliveryCoordinator.drainQueue)
 *   ↓
 * Django REST API (DjangoTelemetryClient.sendTelemetry)
 *   ↓
 * Confirmed success → remove from queue
 * Failure → retain according to retry policy (transient backoff, auth blocked, or terminal dead-letter)
 */
class PhoneTelemetryIngestionHandler(
    val telemetryClient: DjangoTelemetryClient,
    val receiver: WearTransportReceiver = WearTransportReceiver(),
    val queue: TelemetryQueue = DurableTelemetryQueueStore.createTemporary(),
    val deliveryCoordinator: TelemetryDeliveryCoordinator = TelemetryDeliveryCoordinator(queue, telemetryClient)
) {
    /**
     * Ingests a validated TransportEnvelope into the durable queue and attempts delivery:
     * 1. Confirms payloadType is PHYSIOLOGICAL_TELEMETRY
     * 2. Extracts and validates CanonicalTelemetry
     * 3. Enqueues durably into queue (source of truth for pending delivery)
     * 4. Triggers delivery worker to dispatch pending records to Django
     */
    suspend fun handleEnvelope(envelope: TransportEnvelope): TelemetryIngestResult {
        if (envelope.payloadType == TransportEnvelope.PAYLOAD_TYPE_TELEMETRY_BATCH) {
            return handleBatchEnvelope(envelope)
        }

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

        // Enqueue durably BEFORE attempting delivery
        val enqueueResult = queue.enqueue(envelope)
        when (enqueueResult) {
            is EnqueueResult.Duplicate -> {
                return TelemetryIngestResult.MalformedPayloadError(
                    "Duplicate message ID '${envelope.messageId}' already exists in queue"
                )
            }
            is EnqueueResult.QueueFull -> {
                return TelemetryIngestResult.ServerError(
                    statusCode = 507,
                    message = "Queue full (capacity ${enqueueResult.capacity})"
                )
            }
            is EnqueueResult.Rejected -> {
                return TelemetryIngestResult.MalformedPayloadError(enqueueResult.reason)
            }
            is EnqueueResult.Enqueued -> {
                if (BuildConfig.DEBUG) {
                    Log.d(TAG, "Durable enqueue confirmed: messageId=${envelope.messageId}")
                }
            }
        }

        // Only after durable persistence, attempt delivery
        val drainSummary = deliveryCoordinator.drainQueue()
        return drainSummary.lastResult ?: TelemetryIngestResult.Success(201, null)
    }

    /**
     * Ingests a batched TelemetryEnvelope containing multiple CanonicalTelemetry samples.
     * Enqueues each individual sample durably into the queue before attempting delivery.
     */
    suspend fun handleBatchEnvelope(envelope: TransportEnvelope): TelemetryIngestResult {
        val batch = TelemetryBatch.fromJson(envelope.payload)
            ?: return TelemetryIngestResult.MalformedPayloadError(
                "Failed to deserialize TelemetryBatch from payload (messageId=${envelope.messageId})"
            )

        if (batch.samples.isEmpty()) {
            return TelemetryIngestResult.MalformedPayloadError("TelemetryBatch contains no samples (messageId=${envelope.messageId})")
        }

        for ((index, sample) in batch.samples.withIndex()) {
            if (sample.timestamp.isBlank()) {
                return TelemetryIngestResult.MalformedPayloadError(
                    "Sample #$index timestamp cannot be blank in batch ${envelope.messageId}"
                )
            }
            val sampleEnvelope = sample.toTransportEnvelope(
                deviceId = envelope.deviceId,
                messageId = "${envelope.messageId}_$index",
                timestampEpochMs = envelope.timestamp,
                sequenceNumber = envelope.sequenceNumber?.let { it * 1000L + index }
            )
            val enqueueResult = queue.enqueue(sampleEnvelope)
            if (enqueueResult is EnqueueResult.QueueFull) {
                return TelemetryIngestResult.ServerError(
                    statusCode = 507,
                    message = "Queue full (capacity ${enqueueResult.capacity})"
                )
            }
        }

        val drainSummary = deliveryCoordinator.drainQueue()
        return drainSummary.lastResult ?: TelemetryIngestResult.Success(201, null)
    }

    /**
     * Ingests a raw transport payload string through existing envelope validation,
     * extracts CanonicalTelemetry, enqueues durably, and attempts delivery.
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

        /**
         * Factory method to construct an ingestion handler backed by device filesystem.
         */
        fun create(
            context: Context,
            telemetryClient: DjangoTelemetryClient,
            receiver: WearTransportReceiver = WearTransportReceiver(),
            retryPolicy: QueueRetryPolicy = QueueRetryPolicy()
        ): PhoneTelemetryIngestionHandler {
            val queueStore = DurableTelemetryQueueStore.create(context, retryPolicy)
            val coordinator = TelemetryDeliveryCoordinator(queueStore, telemetryClient, retryPolicy)
            return PhoneTelemetryIngestionHandler(
                telemetryClient = telemetryClient,
                receiver = receiver,
                queue = queueStore,
                deliveryCoordinator = coordinator
            )
        }
    }
}
