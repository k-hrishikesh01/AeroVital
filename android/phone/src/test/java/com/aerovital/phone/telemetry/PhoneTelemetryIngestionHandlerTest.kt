package com.aerovital.phone.telemetry

import com.aerovital.phone.data.remote.DjangoTelemetryClient
import com.aerovital.phone.data.remote.TelemetryIngestResult
import com.aerovital.phone.data.remote.TokenProvider
import com.aerovital.phone.transport.WearTransportReceiver
import com.aerovital.shared.telemetry.CanonicalTelemetry
import com.aerovital.shared.transport.TransportEnvelope
import com.google.gson.Gson
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.util.UUID
import java.util.concurrent.TimeUnit

class PhoneTelemetryIngestionHandlerTest {

    private lateinit var mockWebServer: MockWebServer
    private val testToken = "test-token-777"
    private val tokenProvider = TokenProvider { testToken }
    private lateinit var telemetryClient: DjangoTelemetryClient
    private lateinit var receiver: WearTransportReceiver
    private lateinit var handler: PhoneTelemetryIngestionHandler
    private val gson = Gson()

    @Before
    fun setUp() {
        mockWebServer = MockWebServer()
        mockWebServer.start()
        WearTransportReceiver.duplicateCache.clear()
        receiver = WearTransportReceiver()

        telemetryClient = DjangoTelemetryClient.create(
            baseUrl = mockWebServer.url("/").toString(),
            tokenProvider = tokenProvider
        )

        handler = PhoneTelemetryIngestionHandler(
            telemetryClient = telemetryClient,
            receiver = receiver
        )
    }

    @After
    fun tearDown() {
        WearTransportReceiver.telemetryHandler = null
        mockWebServer.shutdown()
    }

    private fun createValidTelemetryEnvelope(
        messageId: String = UUID.randomUUID().toString(),
        timestamp: Long = System.currentTimeMillis(),
        heartRate: Float = 72.0f
    ): TransportEnvelope {
        val telemetry = CanonicalTelemetry(
            timestamp = "2026-09-26T12:00:00.000Z",
            heartRate = heartRate,
            spo2 = 98.0f,
            accelX = 0.05f,
            accelY = 0.10f,
            accelZ = 9.81f,
            rawPayload = mapOf("device_vendor" to "GalaxyWatch")
        )
        return telemetry.toTransportEnvelope(
            deviceId = "watch-galaxy-001",
            messageId = messageId,
            timestampEpochMs = timestamp
        )
    }

    @Test
    fun `valid TransportEnvelope is successfully extracted and posted to Django`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"status": "accumulating", "telemetry": {"id": "tel-001"}}""")
        )

        val envelope = createValidTelemetryEnvelope()
        val result = handler.handleEnvelope(envelope)

        assertTrue("Expected Success, got $result", result is TelemetryIngestResult.Success)
        assertEquals(201, (result as TelemetryIngestResult.Success).statusCode)

        val recordedRequest = mockWebServer.takeRequest(2, TimeUnit.SECONDS)
        assertNotNull(recordedRequest)
        assertEquals("POST", recordedRequest!!.method)
        assertEquals("/api/v1/telemetry/", recordedRequest.path)
        assertEquals("Token $testToken", recordedRequest.getHeader("Authorization"))

        val bodyString = recordedRequest.body.readUtf8()
        val jsonMap = gson.fromJson(bodyString, Map::class.java)
        assertEquals("2026-09-26T12:00:00.000Z", jsonMap["timestamp"])
        assertEquals(72.0, (jsonMap["heart_rate"] as Number).toDouble(), 0.01)
    }

    @Test
    fun `envelope with non-telemetry payloadType returns MalformedPayloadError`() = runTest {
        val nonTelemetryEnvelope = TransportEnvelope(
            version = TransportEnvelope.CURRENT_VERSION,
            messageId = UUID.randomUUID().toString(),
            deviceId = "watch-001",
            timestamp = System.currentTimeMillis(),
            payloadType = TransportEnvelope.PAYLOAD_TYPE_TEST,
            payload = "{}"
        )

        val result = handler.handleEnvelope(nonTelemetryEnvelope)

        assertTrue(result is TelemetryIngestResult.MalformedPayloadError)
        val error = result as TelemetryIngestResult.MalformedPayloadError
        assertTrue(error.reason.contains("does not match expected"))
        assertEquals(0, mockWebServer.requestCount)
    }

    @Test
    fun `envelope with unparsable payload returns MalformedPayloadError`() = runTest {
        val corruptedEnvelope = TransportEnvelope(
            version = TransportEnvelope.CURRENT_VERSION,
            messageId = UUID.randomUUID().toString(),
            deviceId = "watch-001",
            timestamp = System.currentTimeMillis(),
            payloadType = TransportEnvelope.PAYLOAD_TYPE_TELEMETRY,
            payload = "invalid-json-data"
        )

        val result = handler.handleEnvelope(corruptedEnvelope)

        assertTrue(result is TelemetryIngestResult.MalformedPayloadError)
        val error = result as TelemetryIngestResult.MalformedPayloadError
        assertTrue(error.reason.contains("Failed to deserialize"))
        assertEquals(0, mockWebServer.requestCount)
    }

    @Test
    fun `envelope with blank timestamp returns MalformedPayloadError`() = runTest {
        val telemetryWithBlankTimestamp = CanonicalTelemetry(timestamp = "")
        val envelope = telemetryWithBlankTimestamp.toTransportEnvelope(deviceId = "watch-001")

        val result = handler.handleEnvelope(envelope)

        assertTrue(result is TelemetryIngestResult.MalformedPayloadError)
        val error = result as TelemetryIngestResult.MalformedPayloadError
        assertTrue(error.reason.contains("timestamp cannot be blank"))
        assertEquals(0, mockWebServer.requestCount)
    }

    @Test
    fun `handlePayloadString validates envelope and rejects stale message`() = runTest {
        val staleTimestamp = System.currentTimeMillis() - TransportEnvelope.STALE_THRESHOLD_MS - 5000
        val staleEnvelope = createValidTelemetryEnvelope(timestamp = staleTimestamp)
        val jsonString = gson.toJson(staleEnvelope)

        val result = handler.handlePayloadString(jsonString)

        assertTrue(result is TelemetryIngestResult.MalformedPayloadError)
        val error = result as TelemetryIngestResult.MalformedPayloadError
        assertTrue(error.reason.contains("STALE_MESSAGE"))
        assertEquals(0, mockWebServer.requestCount)
    }

    @Test
    fun `handlePayloadString validates envelope and rejects duplicate message ID`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"status": "accumulating"}""")
        )

        val envelope = createValidTelemetryEnvelope(messageId = "fixed-message-uuid-1")
        val jsonString = gson.toJson(envelope)

        // First attempt succeeds
        val result1 = handler.handlePayloadString(jsonString)
        assertTrue(result1 is TelemetryIngestResult.Success)
        assertEquals(1, mockWebServer.requestCount)

        // Second attempt with duplicate messageId must fail without making another network request
        val result2 = handler.handlePayloadString(jsonString)
        assertTrue(result2 is TelemetryIngestResult.MalformedPayloadError)
        val error = result2 as TelemetryIngestResult.MalformedPayloadError
        assertTrue(error.reason.contains("DUPLICATE_MESSAGE"))
        assertEquals(1, mockWebServer.requestCount)
    }

    @Test
    fun `WearTransportReceiver delegates valid envelopes to registered telemetryHandler`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"status": "accumulating"}""")
        )

        WearTransportReceiver.telemetryHandler = handler

        val envelope = createValidTelemetryEnvelope()
        val jsonString = gson.toJson(envelope)

        // Validate via receiver
        val validationResult = receiver.validateAndParse(jsonString)
        assertTrue(validationResult is com.aerovital.shared.transport.TransportResult.Success)

        // Invoke handler
        val result = handler.handleEnvelope((validationResult as com.aerovital.shared.transport.TransportResult.Success).data)
        assertTrue(result is TelemetryIngestResult.Success)
        assertEquals(1, mockWebServer.requestCount)
    }

    @Test
    fun `telemetry is retained in durable queue when backend is offline and delivered upon recovery`() = runTest {
        // 1. Backend is offline (returns 503)
        mockWebServer.enqueue(MockResponse().setResponseCode(503).setBody("Service Unavailable"))

        val envelope = createValidTelemetryEnvelope(messageId = "offline-test-msg")
        val result = handler.handleEnvelope(envelope)

        // Result reflects failure, but record is durably preserved in queue
        assertTrue(result is TelemetryIngestResult.ServerError)
        assertEquals(1, handler.queue.countTotal())
        val queuedRecord = handler.queue.getRecord("offline-test-msg")
        assertNotNull(queuedRecord)
        assertEquals(com.aerovital.phone.queue.DeliveryState.FAILED_RETRYABLE, queuedRecord!!.deliveryState)

        // 2. Backend recovers (returns 201)
        mockWebServer.enqueue(MockResponse().setResponseCode(201).setBody("""{"status": "accumulating"}"""))

        // Drain queue after backoff interval
        val summary = handler.deliveryCoordinator.drainQueue(currentEpochMs = System.currentTimeMillis() + 60_000L)
        assertEquals(1, summary.successCount)
        assertEquals(0, handler.queue.countTotal())
        assertNull(handler.queue.getRecord("offline-test-msg"))
    }
}
