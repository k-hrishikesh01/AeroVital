package com.aerovital.watch.queue

import com.aerovital.shared.transport.TransportEnvelope
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.io.File
import java.util.UUID

class DurableWatchTelemetryBufferTest {

    private lateinit var tempDir: File
    private lateinit var buffer: DurableWatchTelemetryBuffer

    @Before
    fun setUp() {
        tempDir = File(System.getProperty("java.io.tmpdir"), "watch_buffer_test_${UUID.randomUUID()}")
        tempDir.mkdirs()
        buffer = DurableWatchTelemetryBuffer(
            storageDir = tempDir,
            maxCapacity = 5,
            baseRetryDelayMs = 1000L,
            maxRetryDelayMs = 8000L,
            maxRetryAttempts = 5
        )
    }

    @After
    fun tearDown() {
        tempDir.deleteRecursively()
    }

    private fun createEnvelope(
        messageId: String = UUID.randomUUID().toString(),
        sequenceNumber: Long = 1L,
        timestamp: Long = System.currentTimeMillis(),
        batchId: String = "batch-$sequenceNumber"
    ): TransportEnvelope {
        return TransportEnvelope(
            version = TransportEnvelope.CURRENT_VERSION,
            messageId = messageId,
            deviceId = "watch-test-01",
            timestamp = timestamp,
            payloadType = TransportEnvelope.PAYLOAD_TYPE_TELEMETRY_BATCH,
            payload = "{\"batchId\":\"$batchId\",\"samples\":[]}",
            sequenceNumber = sequenceNumber,
            batchId = batchId
        )
    }

    @Test
    fun `enqueue persists record to disk and is retained until explicit acknowledgement`() {
        val env = createEnvelope(messageId = "batch-101", sequenceNumber = 1L)
        val result = buffer.enqueue(env)

        assertTrue(result is WatchEnqueueResult.Enqueued)
        assertEquals(1, buffer.countPending())
        assertEquals(1, buffer.countTotal())

        val diskFile = File(tempDir, "batch-101.json")
        assertTrue("Expected JSON file to exist on disk", diskFile.exists())

        // Record must NOT disappear on peek or query
        val pending = buffer.peekPending(10)
        assertEquals(1, pending.size)
        assertEquals("batch-101", pending[0].messageId)
        assertEquals(1, buffer.countPending())
    }

    @Test
    fun `reloadFromDisk recovers all unacknowledged batches after process termination`() {
        val env1 = createEnvelope(messageId = "batch-01", sequenceNumber = 1L, timestamp = 1000L)
        val env2 = createEnvelope(messageId = "batch-02", sequenceNumber = 2L, timestamp = 2000L)
        buffer.enqueue(env1)
        buffer.enqueue(env2)

        assertEquals(2, buffer.countPending())

        // Simulate complete process death & restart with new buffer instance pointing to same storageDir
        val recoveredBuffer = DurableWatchTelemetryBuffer(
            storageDir = tempDir,
            maxCapacity = 5
        )

        assertEquals(2, recoveredBuffer.countPending())
        assertEquals(2, recoveredBuffer.countTotal())

        val pending = recoveredBuffer.peekPending(10)
        assertEquals(2, pending.size)
        assertEquals("batch-01", pending[0].messageId)
        assertEquals("batch-02", pending[1].messageId)
    }

    @Test
    fun `markAcknowledged atomically deletes confirmed batch from disk`() {
        val env = createEnvelope(messageId = "batch-ack-test")
        buffer.enqueue(env)

        val diskFile = File(tempDir, "batch-ack-test.json")
        assertTrue(diskFile.exists())

        val removed = buffer.markAcknowledged("batch-ack-test")
        assertTrue(removed)
        assertEquals(0, buffer.countPending())
        assertEquals(0, buffer.countTotal())
        assertFalse("Expected JSON file to be deleted from disk upon ACK", diskFile.exists())

        // Second ack call returns false
        assertFalse(buffer.markAcknowledged("batch-ack-test"))
    }

    @Test
    fun `peekPending preserves strict chronological ordering by sequence number`() {
        // Enqueue out of order
        val env3 = createEnvelope(messageId = "batch-c", sequenceNumber = 30L, timestamp = 3000L)
        val env1 = createEnvelope(messageId = "batch-a", sequenceNumber = 10L, timestamp = 1000L)
        val env2 = createEnvelope(messageId = "batch-b", sequenceNumber = 20L, timestamp = 2000L)

        buffer.enqueue(env3)
        buffer.enqueue(env1)
        buffer.enqueue(env2)

        val pending = buffer.peekPending(10)
        assertEquals(3, pending.size)
        assertEquals("batch-a", pending[0].messageId)
        assertEquals("batch-b", pending[1].messageId)
        assertEquals("batch-c", pending[2].messageId)
        assertEquals(10L, pending[0].sequenceNumber)
        assertEquals(20L, pending[1].sequenceNumber)
        assertEquals(30L, pending[2].sequenceNumber)
    }

    @Test
    fun `duplicate message ID is rejected without writing duplicate files`() {
        val env = createEnvelope(messageId = "batch-unique-1")
        val res1 = buffer.enqueue(env)
        assertTrue(res1 is WatchEnqueueResult.Enqueued)

        val res2 = buffer.enqueue(env)
        assertTrue(res2 is WatchEnqueueResult.Duplicate)
        assertEquals(1, buffer.countTotal())
    }

    @Test
    fun `disconnection does not increment attempt count while backoff does on transmission failure`() {
        val env = createEnvelope(messageId = "retry-test-1")
        buffer.enqueue(env)

        val now = 10000L
        // 1. Bluetooth disconnected: attempt count unchanged, immediately retryable upon reconnection
        buffer.markTransmissionFailure("retry-test-1", isLinkConnected = false, currentEpochMs = now)
        val rec1 = buffer.getRecord("retry-test-1")
        assertNotNull(rec1)
        assertEquals(0, rec1!!.attemptCount)
        assertNull(rec1.nextRetryEpochMs)

        // 2. Link connected but transmission failed: attempt count increments and exponential backoff kicks in
        val t2 = now + 1000L
        buffer.markTransmissionFailure("retry-test-1", isLinkConnected = true, currentEpochMs = t2)
        val rec2 = buffer.getRecord("retry-test-1")
        assertEquals(1, rec2!!.attemptCount)
        assertEquals(t2 + 1000L, rec2.nextRetryEpochMs) // 1000 * 2^0 = 1000

        val t3 = t2 + 1000L
        buffer.markTransmissionFailure("retry-test-1", isLinkConnected = true, currentEpochMs = t3)
        val rec3 = buffer.getRecord("retry-test-1")
        assertEquals(2, rec3!!.attemptCount)
        assertEquals(t3 + 2000L, rec3.nextRetryEpochMs) // 1000 * 2^1 = 2000
    }

    @Test
    fun `capacity enforcement safely drops oldest record on overflow to protect watch storage`() {
        // Capacity is 5
        for (i in 1..5) {
            val env = createEnvelope(messageId = "batch-cap-$i", sequenceNumber = i.toLong(), timestamp = i * 1000L)
            val res = buffer.enqueue(env)
            assertTrue(res is WatchEnqueueResult.Enqueued)
        }
        assertEquals(5, buffer.countTotal())

        // 6th item causes safe eviction of oldest (batch-cap-1)
        val env6 = createEnvelope(messageId = "batch-cap-6", sequenceNumber = 6L, timestamp = 6000L)
        val res6 = buffer.enqueue(env6)
        assertTrue(res6 is WatchEnqueueResult.OverflowEvictedOldest)
        assertEquals("batch-cap-1", (res6 as WatchEnqueueResult.OverflowEvictedOldest).evictedMessageId)
        assertEquals("batch-cap-6", res6.enqueuedMessageId)

        assertEquals(5, buffer.countTotal())
        assertNull(buffer.getRecord("batch-cap-1"))
        assertNotNull(buffer.getRecord("batch-cap-6"))
        assertFalse(File(tempDir, "batch-cap-1.json").exists())
        assertTrue(File(tempDir, "batch-cap-6.json").exists())
    }

    @Test
    fun `corrupted files on disk are quarantined and skipped without crashing`() {
        val corruptedFile = File(tempDir, "corrupted-file.json")
        corruptedFile.writeText("NOT_VALID_JSON{{{")

        val newBuffer = DurableWatchTelemetryBuffer(storageDir = tempDir)
        assertEquals(0, newBuffer.countTotal())

        val quarantined = File(tempDir, "corrupted-file.json.corrupted")
        assertTrue("Corrupted file must be renamed to .corrupted", quarantined.exists())
    }
}
