package com.aerovital.phone.transport

import com.aerovital.phone.data.remote.DjangoTelemetryClient
import com.aerovital.phone.data.remote.TokenProvider
import com.aerovital.phone.telemetry.PhoneTelemetryIngestionHandler
import com.aerovital.shared.telemetry.CanonicalTelemetry
import com.aerovital.shared.transport.TelemetryAck
import com.aerovital.shared.transport.TelemetryBatch
import com.aerovital.shared.transport.TransportEnvelope
import com.google.gson.Gson
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.util.UUID

class WearTransportReceiverAckTest {

    private lateinit var mockWebServer: MockWebServer
    private lateinit var receiver: WearTransportReceiver
    private lateinit var fakeAckSender: FakePhoneAckSender
    private lateinit var handler: PhoneTelemetryIngestionHandler
    private val gson = Gson()

    @Before
    fun setUp() {
        mockWebServer = MockWebServer()
        mockWebServer.start()
        WearTransportReceiver.duplicateCache.clear()

        receiver = WearTransportReceiver()
        fakeAckSender = FakePhoneAckSender()
        WearTransportReceiver.customAckSender = fakeAckSender

        val client = DjangoTelemetryClient.create(
            baseUrl = mockWebServer.url("/").toString(),
            tokenProvider = TokenProvider { "test-token" }
        )
        handler = PhoneTelemetryIngestionHandler(
            telemetryClient = client,
            receiver = receiver
        )
        WearTransportReceiver.telemetryHandler = handler
    }

    @After
    fun tearDown() {
        WearTransportReceiver.customAckSender = null
        WearTransportReceiver.telemetryHandler = null
        mockWebServer.shutdown()
    }

    @Test
    fun `valid single telemetry envelope dispatches explicit STORED ACK to source node`() = runTest {
        mockWebServer.enqueue(MockResponse().setResponseCode(201).setBody("""{"status":"accumulating"}"""))

        val telemetry = CanonicalTelemetry(
            timestamp = "2026-11-25T14:00:00Z",
            heartRate = 76f,
            accelX = 0.1f,
            accelY = 9.8f,
            accelZ = -0.1f
        )
        val envelope = telemetry.toTransportEnvelope(
            deviceId = "watch-01",
            messageId = "msg-ack-test-1",
            sequenceNumber = 42L
        )

        receiver.handleReceivedEnvelope(gson.toJson(envelope), sourceNodeId = "watch-node-abc")

        assertEquals(1, fakeAckSender.dispatchedAcks.size)
        val (nodeId, ack) = fakeAckSender.dispatchedAcks[0]
        assertEquals("watch-node-abc", nodeId)
        assertEquals("msg-ack-test-1", ack.messageId)
        assertEquals(42L, ack.sequenceNumber)
        assertEquals(TelemetryAck.STATUS_STORED, ack.status)
    }

    @Test
    fun `valid telemetry batch envelope enqueues all samples and dispatches single batch ACK`() = runTest {
        // Enqueue 2 responses for 2 samples in the batch
        mockWebServer.enqueue(MockResponse().setResponseCode(201).setBody("""{"status":"accumulating"}"""))
        mockWebServer.enqueue(MockResponse().setResponseCode(201).setBody("""{"status":"accumulating"}"""))

        val samples = listOf(
            CanonicalTelemetry(timestamp = "2026-11-25T14:00:01Z", heartRate = 72f),
            CanonicalTelemetry(timestamp = "2026-11-25T14:00:02Z", heartRate = 74f)
        )
        val batch = TelemetryBatch(batchId = "batch-xyz-99", samples = samples)
        val envelope = TransportEnvelope(
            version = TransportEnvelope.CURRENT_VERSION,
            messageId = "batch-xyz-99",
            deviceId = "watch-01",
            timestamp = System.currentTimeMillis(),
            payloadType = TransportEnvelope.PAYLOAD_TYPE_TELEMETRY_BATCH,
            payload = batch.toJson(),
            sequenceNumber = 99L,
            batchId = "batch-xyz-99"
        )

        receiver.handleReceivedEnvelope(gson.toJson(envelope), sourceNodeId = "watch-node-xyz")

        assertEquals(1, fakeAckSender.dispatchedAcks.size)
        val (nodeId, ack) = fakeAckSender.dispatchedAcks[0]
        assertEquals("watch-node-xyz", nodeId)
        assertEquals("batch-xyz-99", ack.messageId)
        assertEquals("batch-xyz-99", ack.batchId)
        assertEquals(99L, ack.sequenceNumber)
        assertEquals(TelemetryAck.STATUS_STORED, ack.status)
    }

    @Test
    fun `duplicate envelope transmission triggers DUPLICATE ACK to stop watch retries`() = runTest {
        mockWebServer.enqueue(MockResponse().setResponseCode(201).setBody("""{"status":"accumulating"}"""))

        val telemetry = CanonicalTelemetry(
            timestamp = "2026-11-25T14:00:00Z",
            heartRate = 80f
        )
        val envelope = telemetry.toTransportEnvelope(
            deviceId = "watch-01",
            messageId = "msg-dup-1"
        )
        val json = gson.toJson(envelope)

        // First pass: STORED ACK
        receiver.handleReceivedEnvelope(json, sourceNodeId = "watch-node-1")
        assertEquals(1, fakeAckSender.dispatchedAcks.size)
        assertEquals(TelemetryAck.STATUS_STORED, fakeAckSender.dispatchedAcks[0].second.status)

        // Second pass: Duplicate received, must send DUPLICATE ACK
        receiver.handleReceivedEnvelope(json, sourceNodeId = "watch-node-1")
        assertEquals(2, fakeAckSender.dispatchedAcks.size)
        val secondAck = fakeAckSender.dispatchedAcks[1].second
        assertEquals("msg-dup-1", secondAck.messageId)
        assertEquals(TelemetryAck.STATUS_DUPLICATE, secondAck.status)
    }
}

class FakePhoneAckSender : PhoneAckSender {
    val dispatchedAcks = mutableListOf<Pair<String, TelemetryAck>>()

    override suspend fun sendAck(nodeId: String, ack: TelemetryAck): Boolean {
        dispatchedAcks.add(Pair(nodeId, ack))
        return true
    }
}
