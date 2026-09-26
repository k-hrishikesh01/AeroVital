package com.aerovital.phone.transport

import com.aerovital.shared.transport.ErrorReason
import com.aerovital.shared.transport.TransportEnvelope
import com.aerovital.shared.transport.TransportResult
import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.assertFalse
import org.junit.Before
import org.junit.Test

class WearTransportReceiverTest {

    private val gson = Gson()
    private lateinit var receiver: WearTransportReceiver

    @Before
    fun setup() {
        WearTransportReceiver.duplicateCache.clear()
        receiver = WearTransportReceiver()
    }

    private fun createValidEnvelope(messageId: String = "msg-123", timestamp: Long = System.currentTimeMillis()): TransportEnvelope {
        return TransportEnvelope(
            version = TransportEnvelope.CURRENT_VERSION,
            messageId = messageId,
            deviceId = "wear-001",
            timestamp = timestamp,
            payloadType = TransportEnvelope.PAYLOAD_TYPE_TEST,
            payload = "{}"
        )
    }

    @Test
    fun `validateAndParse succeeds for valid JSON envelope`() {
        val env = createValidEnvelope()
        val json = gson.toJson(env)

        val result = receiver.validateAndParse(json)
        
        assertTrue(result is TransportResult.Success)
        assertEquals(env.messageId, (result as TransportResult.Success).data.messageId)
    }

    @Test
    fun `validateAndParse fails for malformed JSON`() {
        val result = receiver.validateAndParse("not json")
        
        assertTrue(result is TransportResult.Error)
        assertEquals(ErrorReason.MALFORMED_ENVELOPE, (result as TransportResult.Error).reason)
    }

    @Test
    fun `validateAndParse fails for unsupported version`() {
        val env = createValidEnvelope().copy(version = 999)
        val result = receiver.validateAndParse(gson.toJson(env))
        
        assertTrue(result is TransportResult.Error)
        assertEquals(ErrorReason.UNSUPPORTED_VERSION, (result as TransportResult.Error).reason)
    }

    @Test
    fun `validateAndParse fails for stale message`() {
        val staleTimestamp = System.currentTimeMillis() - TransportEnvelope.STALE_THRESHOLD_MS - 1000
        val env = createValidEnvelope(timestamp = staleTimestamp)
        
        val result = receiver.validateAndParse(gson.toJson(env))
        
        assertTrue(result is TransportResult.Error)
        assertEquals(ErrorReason.STALE_MESSAGE, (result as TransportResult.Error).reason)
    }

    @Test
    fun `validateAndParse fails on duplicate message ID`() {
        val env = createValidEnvelope("msg-duplicate")
        val json = gson.toJson(env)

        // First pass succeeds
        val result1 = receiver.validateAndParse(json)
        assertTrue(result1 is TransportResult.Success)

        // Second pass fails
        val result2 = receiver.validateAndParse(json)
        assertTrue(result2 is TransportResult.Error)
        assertEquals(ErrorReason.DUPLICATE_MESSAGE, (result2 as TransportResult.Error).reason)
    }

    @Test
    fun `DuplicateMessageCache rejects duplicates`() {
        val cache = DuplicateMessageCache(3)
        assertTrue(cache.addIfNotSeen("1"))
        assertTrue(cache.addIfNotSeen("2"))
        assertFalse(cache.addIfNotSeen("1")) // Duplicate
    }

    @Test
    fun `DuplicateMessageCache evicts eldest`() {
        val cache = DuplicateMessageCache(3)
        assertTrue(cache.addIfNotSeen("1"))
        assertTrue(cache.addIfNotSeen("2"))
        assertTrue(cache.addIfNotSeen("3"))
        
        // This should evict "1"
        assertTrue(cache.addIfNotSeen("4"))
        
        // Now "1" is no longer seen
        assertTrue(cache.addIfNotSeen("1"))
    }
}
