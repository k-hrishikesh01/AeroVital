package com.aerovital.phone.queue

import com.aerovital.shared.telemetry.CanonicalTelemetry
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

class DurableTelemetryQueueStoreTest {

    private lateinit var tempDir: File
    private lateinit var store: DurableTelemetryQueueStore
    private val policy = QueueRetryPolicy(
        initialBackoffMs = 1_000L,
        backoffMultiplier = 2.0,
        maxBackoffMs = 10_000L,
        maxDeliveryAttempts = 3,
        maxQueueCapacity = 5
    )

    @Before
    fun setUp() {
        val baseDir = File(System.getProperty("java.io.tmpdir") ?: "/tmp")
        tempDir = File(baseDir, "aerovital_test_queue_${UUID.randomUUID()}")
        tempDir.mkdirs()
        store = DurableTelemetryQueueStore(tempDir, retryPolicy = policy)
    }

    @After
    fun tearDown() {
        tempDir.deleteRecursively()
    }

    private fun createEnvelope(
        messageId: String = UUID.randomUUID().toString(),
        timestamp: Long = 1700000000000L,
        sequenceNumber: Long? = 1L
    ): TransportEnvelope {
        val telemetry = CanonicalTelemetry(
            timestamp = "2026-09-26T12:00:00.000Z",
            heartRate = 72.0f,
            accelX = 0.01f,
            accelY = 0.02f,
            accelZ = 9.81f
        )
        return telemetry.toTransportEnvelope(
            deviceId = "watch-001",
            messageId = messageId,
            timestampEpochMs = timestamp,
            sequenceNumber = sequenceNumber
        )
    }

    @Test
    fun `enqueue valid telemetry creates atomic file on disk`() {
        val envelope = createEnvelope(messageId = "msg-001")
        val result = store.enqueue(envelope)

        assertTrue(result is EnqueueResult.Enqueued)
        assertEquals("msg-001", (result as EnqueueResult.Enqueued).messageId)
        assertEquals(1, store.countTotal())
        assertEquals(1, store.countPending())

        val recordFile = File(tempDir, "msg-001.json")
        assertTrue("Record file must exist on disk", recordFile.exists())
        assertTrue("Record file must not be empty", recordFile.length() > 0)
    }

    @Test
    fun `persistence across store recreation restores all records`() {
        val env1 = createEnvelope(messageId = "persist-001", timestamp = 1700000001000L)
        val env2 = createEnvelope(messageId = "persist-002", timestamp = 1700000002000L)
        store.enqueue(env1)
        store.enqueue(env2)

        store.markRetryableFailure("persist-001", "NETWORK_ERROR", "Timeout", 2000L, 1700000003000L)

        // Simulate application process restart by creating a new store instance pointing to the same directory
        val reloadedStore = DurableTelemetryQueueStore(tempDir, retryPolicy = policy)

        assertEquals(2, reloadedStore.countTotal())
        val record1 = reloadedStore.getRecord("persist-001")
        assertNotNull(record1)
        assertEquals(1, record1!!.attemptCount)
        assertEquals(DeliveryState.FAILED_RETRYABLE, record1.deliveryState)
        assertEquals("NETWORK_ERROR", record1.lastFailureClassification)
        assertEquals("Timeout", record1.lastFailureMessage)

        val record2 = reloadedStore.getRecord("persist-002")
        assertNotNull(record2)
        assertEquals(0, record2!!.attemptCount)
        assertEquals(DeliveryState.PENDING, record2.deliveryState)
    }

    @Test
    fun `duplicate message ID is rejected without creating duplicate records or files`() {
        val env = createEnvelope(messageId = "dup-001")
        val res1 = store.enqueue(env)
        assertTrue(res1 is EnqueueResult.Enqueued)

        val res2 = store.enqueue(env)
        assertTrue(res2 is EnqueueResult.Duplicate)
        assertEquals(1, store.countTotal())

        val matchingFiles = tempDir.listFiles { _, name -> name.startsWith("dup-001") }
        assertEquals(1, matchingFiles?.size)
    }

    @Test
    fun `dequeue and remove after successful delivery deletes file from disk`() {
        val env = createEnvelope(messageId = "deliv-001")
        store.enqueue(env)
        val recordFile = File(tempDir, "deliv-001.json")
        assertTrue(recordFile.exists())

        val removed = store.markSuccess("deliv-001")
        assertTrue(removed)
        assertEquals(0, store.countTotal())
        assertNull(store.getRecord("deliv-001"))
        assertFalse("File must be deleted from disk upon confirmed delivery", recordFile.exists())
    }

    @Test
    fun `retention after transient failure persists state and updates metadata`() {
        val env = createEnvelope(messageId = "fail-001")
        store.enqueue(env)

        store.markRetryableFailure("fail-001", "NETWORK_ERROR", "Host unreachable", 1000L, 5000L)

        val record = store.getRecord("fail-001")
        assertNotNull(record)
        assertEquals(1, record!!.attemptCount)
        assertEquals(DeliveryState.FAILED_RETRYABLE, record.deliveryState)
        assertEquals(6000L, record.nextRetryEpochMs)
        assertEquals("NETWORK_ERROR", record.lastFailureClassification)
        assertEquals("Host unreachable", record.lastFailureMessage)
    }

    @Test
    fun `ordering delivers records deterministically by observation timestamp and sequence number`() {
        // Enqueue out of order
        val env3 = createEnvelope(messageId = "order-3", timestamp = 3000L, sequenceNumber = 3L)
        val env1 = createEnvelope(messageId = "order-1", timestamp = 1000L, sequenceNumber = 1L)
        val env2 = createEnvelope(messageId = "order-2", timestamp = 2000L, sequenceNumber = 2L)

        store.enqueue(env3)
        store.enqueue(env1)
        store.enqueue(env2)

        val pending = store.peekPending(10, currentEpochMs = 10000L)
        assertEquals(3, pending.size)
        assertEquals("order-1", pending[0].messageId)
        assertEquals("order-2", pending[1].messageId)
        assertEquals("order-3", pending[2].messageId)
    }

    @Test
    fun `ordering tie breaker respects sequence number when timestamps match`() {
        val env2 = createEnvelope(messageId = "seq-2", timestamp = 5000L, sequenceNumber = 2L)
        val env1 = createEnvelope(messageId = "seq-1", timestamp = 5000L, sequenceNumber = 1L)

        store.enqueue(env2)
        store.enqueue(env1)

        val pending = store.peekPending(10)
        assertEquals("seq-1", pending[0].messageId)
        assertEquals("seq-2", pending[1].messageId)
    }

    @Test
    fun `queue capacity limits reject new enqueues when full without deleting existing records`() {
        // Policy maxQueueCapacity is 5
        for (i in 1..5) {
            val env = createEnvelope(messageId = "cap-$i")
            val res = store.enqueue(env)
            assertTrue(res is EnqueueResult.Enqueued)
        }
        assertEquals(5, store.countTotal())

        // 6th enqueue should be rejected as QueueFull
        val overflowEnv = createEnvelope(messageId = "cap-overflow")
        val overflowRes = store.enqueue(overflowEnv)
        assertTrue(overflowRes is EnqueueResult.QueueFull)
        assertEquals(5, store.countTotal())

        // Ensure original 5 records are completely preserved
        assertNotNull(store.getRecord("cap-1"))
        assertNotNull(store.getRecord("cap-5"))
        assertNull(store.getRecord("cap-overflow"))
    }
}
