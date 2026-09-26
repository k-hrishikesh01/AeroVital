package com.aerovital.shared.transport

import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TransportEnvelopeTest {

    private val gson = Gson()

    private fun createValidEnvelope(
        timestamp: Long = 1000000L,
        payloadType: String = TransportEnvelope.PAYLOAD_TYPE_TEST
    ) = TransportEnvelope(
        version = TransportEnvelope.CURRENT_VERSION,
        messageId = "msg-123",
        deviceId = "watch-abc",
        timestamp = timestamp,
        payloadType = payloadType,
        payload = "{}"
    )

    @Test
    fun `validate returns success for well-formed envelope`() {
        val currentTime = 1000000L
        val env = createValidEnvelope(timestamp = currentTime)
        val result = TransportEnvelope.validate(env, currentTime)
        assertTrue(result is TransportResult.Success)
    }

    @Test
    fun `validate fails for unsupported version`() {
        val env = createValidEnvelope().copy(version = 99)
        val result = TransportEnvelope.validate(env, 1000000L)
        assertTrue(result is TransportResult.Error)
        assertEquals(ErrorReason.UNSUPPORTED_VERSION, (result as TransportResult.Error).reason)
    }

    @Test
    fun `validate fails for unknown payload type`() {
        val env = createValidEnvelope(payloadType = "BOGUS_TYPE")
        val result = TransportEnvelope.validate(env, 1000000L)
        assertTrue(result is TransportResult.Error)
        assertEquals(ErrorReason.UNKNOWN_PAYLOAD_TYPE, (result as TransportResult.Error).reason)
    }

    @Test
    fun `validate fails for missing string fields`() {
        val env1 = createValidEnvelope().copy(messageId = "   ")
        val result1 = TransportEnvelope.validate(env1, 1000000L)
        assertTrue(result1 is TransportResult.Error)
        assertEquals(ErrorReason.MALFORMED_ENVELOPE, (result1 as TransportResult.Error).reason)
        
        val env2 = createValidEnvelope().copy(payload = "")
        val result2 = TransportEnvelope.validate(env2, 1000000L)
        assertTrue(result2 is TransportResult.Error)
        assertEquals(ErrorReason.MALFORMED_ENVELOPE, (result2 as TransportResult.Error).reason)
    }

    @Test
    fun `validate succeeds for future timestamp within skew tolerance`() {
        val currentTime = 1000000L
        // Envelope is 4 seconds in the future (within 5s tolerance)
        val env = createValidEnvelope(timestamp = currentTime + 4000L)
        val result = TransportEnvelope.validate(env, currentTime)
        assertTrue(result is TransportResult.Success)
    }

    @Test
    fun `validate fails for future timestamp beyond skew tolerance`() {
        val currentTime = 1000000L
        // Envelope is 6 seconds in the future (outside 5s tolerance)
        val env = createValidEnvelope(timestamp = currentTime + 6000L)
        val result = TransportEnvelope.validate(env, currentTime)
        assertTrue(result is TransportResult.Error)
        assertEquals(ErrorReason.FUTURE_TIMESTAMP, (result as TransportResult.Error).reason)
    }

    @Test
    fun `validate fails for stale timestamp`() {
        val currentTime = 1000000L + TransportEnvelope.STALE_THRESHOLD_MS + 1000L
        val env = createValidEnvelope(timestamp = 1000000L)
        val result = TransportEnvelope.validate(env, currentTime)
        assertTrue(result is TransportResult.Error)
        assertEquals(ErrorReason.STALE_MESSAGE, (result as TransportResult.Error).reason)
    }

    @Test
    fun `envelope serializes and deserializes correctly`() {
        val original = TransportEnvelope(
            version = 1,
            messageId = "msg-123",
            deviceId = "watch-abc",
            timestamp = 1690000000000L,
            payloadType = TransportEnvelope.PAYLOAD_TYPE_TEST,
            payload = "{\"test\":true}",
            sequenceNumber = 42L
        )

        val json = gson.toJson(original)
        val deserialized = gson.fromJson(json, TransportEnvelope::class.java)

        assertEquals(original.version, deserialized.version)
        assertEquals(original.messageId, deserialized.messageId)
        assertEquals(original.payload, deserialized.payload)
        assertEquals(original.sequenceNumber, deserialized.sequenceNumber)
    }
}
