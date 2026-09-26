package com.aerovital.watch.transport

import com.aerovital.shared.transport.ErrorReason
import com.aerovital.shared.transport.TransportEnvelope
import com.aerovital.shared.transport.TransportResult
import com.google.gson.Gson
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class WearTransportSenderTest {

    private val gson = Gson()

    private fun createValidEnvelope() = TransportEnvelope(
        version = TransportEnvelope.CURRENT_VERSION,
        messageId = "msg-123",
        deviceId = "wear-001",
        timestamp = System.currentTimeMillis(),
        payloadType = TransportEnvelope.PAYLOAD_TYPE_TEST,
        payload = "{}"
    )

    @Test
    fun `sendEnvelope fails on malformed envelope`() = runBlocking {
        val sender = WearTransportSender(
            nodeProvider = FakeNodeProvider(listOf("node1")),
            messageSender = FakeMessageSender()
        )

        val invalidEnvelope = createValidEnvelope().copy(version = 0)
        val result = sender.sendEnvelope(invalidEnvelope)
        
        assertTrue(result is TransportResult.Error)
        assertEquals(ErrorReason.MALFORMED_ENVELOPE, (result as TransportResult.Error).reason)
    }

    @Test
    fun `sendEnvelope fails when no nodes connected`() = runBlocking {
        val sender = WearTransportSender(
            nodeProvider = FakeNodeProvider(emptyList()),
            messageSender = FakeMessageSender()
        )

        val result = sender.sendEnvelope(createValidEnvelope())
        
        assertTrue(result is TransportResult.Error)
        assertEquals(ErrorReason.NO_NODES_CONNECTED, (result as TransportResult.Error).reason)
    }

    @Test
    fun `sendEnvelope succeeds when node connected and properly serializes`() = runBlocking {
        val fakeMessageSender = FakeMessageSender()
        val sender = WearTransportSender(
            nodeProvider = FakeNodeProvider(listOf("node1")),
            messageSender = fakeMessageSender
        )

        val originalEnvelope = createValidEnvelope()
        val result = sender.sendEnvelope(originalEnvelope)
        
        assertTrue(result is TransportResult.Success)
        assertEquals(1, fakeMessageSender.sentMessages.size)
        assertEquals("/aerovital/telemetry/v1", fakeMessageSender.sentMessages[0].path)
        assertEquals("node1", fakeMessageSender.sentMessages[0].nodeId)
        
        // Test actual serialization matches
        val sentString = String(fakeMessageSender.sentMessages[0].data, Charsets.UTF_8)
        val deserialized = gson.fromJson(sentString, TransportEnvelope::class.java)
        
        assertEquals(originalEnvelope.version, deserialized.version)
        assertEquals(originalEnvelope.messageId, deserialized.messageId)
        assertEquals(originalEnvelope.payloadType, deserialized.payloadType)
        assertEquals(originalEnvelope.deviceId, deserialized.deviceId)
    }
}

class FakeNodeProvider(private val nodes: List<String>) : NodeProvider {
    override suspend fun getConnectedNodeIds(): List<String> = nodes
}

class FakeMessageSender : MessageSender {
    data class SentMessage(val nodeId: String, val path: String, val data: ByteArray)
    val sentMessages = mutableListOf<SentMessage>()

    override suspend fun sendMessage(nodeId: String, path: String, data: ByteArray) {
        sentMessages.add(SentMessage(nodeId, path, data))
    }
}
