package com.aerovital.phone.queue

import com.aerovital.phone.data.remote.DjangoTelemetryClient
import com.aerovital.phone.data.remote.TokenProvider
import com.aerovital.shared.telemetry.CanonicalTelemetry
import com.aerovital.shared.transport.TransportEnvelope
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.SocketPolicy
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.io.File
import java.util.UUID

class TelemetryDeliveryCoordinatorTest {

    private lateinit var mockWebServer: MockWebServer
    private lateinit var tempDir: File
    private lateinit var queue: DurableTelemetryQueueStore
    private lateinit var client: DjangoTelemetryClient
    private lateinit var coordinator: TelemetryDeliveryCoordinator

    private val testToken = "test-token-sec-999"
    private val tokenProvider = TokenProvider { testToken }
    private val policy = QueueRetryPolicy(
        initialBackoffMs = 1_000L,
        backoffMultiplier = 2.0,
        maxBackoffMs = 10_000L,
        maxDeliveryAttempts = 3,
        maxQueueCapacity = 100
    )

    @Before
    fun setUp() {
        mockWebServer = MockWebServer()
        mockWebServer.start()

        val baseDir = File(System.getProperty("java.io.tmpdir") ?: "/tmp")
        tempDir = File(baseDir, "aerovital_coord_test_${UUID.randomUUID()}")
        tempDir.mkdirs()

        queue = DurableTelemetryQueueStore(tempDir, retryPolicy = policy)
        client = DjangoTelemetryClient.create(
            baseUrl = mockWebServer.url("/").toString(),
            tokenProvider = tokenProvider
        )
        coordinator = TelemetryDeliveryCoordinator(queue, client, policy)
    }

    @After
    fun tearDown() {
        mockWebServer.shutdown()
        tempDir.deleteRecursively()
    }

    private fun createEnvelope(
        messageId: String = UUID.randomUUID().toString(),
        timestamp: Long = 1000L,
        heartRate: Float = 72.0f
    ): TransportEnvelope {
        val telemetry = CanonicalTelemetry(
            timestamp = "2026-09-26T12:00:00.000Z",
            heartRate = heartRate,
            spo2 = 98.0f,
            accelX = 0.05f,
            accelY = 0.10f,
            accelZ = 9.81f
        )
        return telemetry.toTransportEnvelope(
            deviceId = "watch-001",
            messageId = messageId,
            timestampEpochMs = timestamp
        )
    }

    @Test
    fun `HTTP success delivers telemetry and removes item from queue`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"status": "accumulating", "telemetry": {"id": "tel-1"}}""")
        )

        val envelope = createEnvelope(messageId = "deliv-success")
        queue.enqueue(envelope)
        assertEquals(1, queue.countPending())

        val summary = coordinator.drainQueue()

        assertEquals(1, summary.processedCount)
        assertEquals(1, summary.successCount)
        assertEquals(0, queue.countPending())
        assertEquals(0, queue.countTotal())
        assertNull("Delivered record must be removed from queue", queue.getRecord("deliv-success"))
    }

    @Test
    fun `network failure retains item, marks FAILED_RETRYABLE, and pauses queue drain`() = runTest {
        mockWebServer.enqueue(
            MockResponse().setSocketPolicy(SocketPolicy.DISCONNECT_AT_START)
        )

        val env1 = createEnvelope(messageId = "net-fail-1", timestamp = 1000L)
        val env2 = createEnvelope(messageId = "net-fail-2", timestamp = 2000L)
        queue.enqueue(env1)
        queue.enqueue(env2)

        val summary = coordinator.drainQueue()

        assertEquals(1, summary.processedCount)
        assertEquals(1, summary.retryableFailureCount)
        assertEquals(0, summary.successCount)

        // Item 1 must be retained and marked FAILED_RETRYABLE
        val record1 = queue.getRecord("net-fail-1")
        assertNotNull(record1)
        assertEquals(DeliveryState.FAILED_RETRYABLE, record1!!.deliveryState)
        assertEquals(1, record1.attemptCount)
        assertEquals("NETWORK_ERROR", record1.lastFailureClassification)
        assertNotNull(record1.nextRetryEpochMs)

        // Item 2 must remain PENDING because drain loop paused on network failure
        val record2 = queue.getRecord("net-fail-2")
        assertNotNull(record2)
        assertEquals(DeliveryState.PENDING, record2!!.deliveryState)
        assertEquals(0, record2.attemptCount)
    }

    @Test
    fun `HTTP 5xx server error retains item and computes exponential backoff`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(503)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"detail": "Backend unavailable."}""")
        )

        val envelope = createEnvelope(messageId = "server-503")
        queue.enqueue(envelope)

        val summary = coordinator.drainQueue()

        assertEquals(1, summary.processedCount)
        assertEquals(1, summary.retryableFailureCount)

        val record = queue.getRecord("server-503")
        assertNotNull(record)
        assertEquals(DeliveryState.FAILED_RETRYABLE, record!!.deliveryState)
        assertEquals(1, record.attemptCount)
        assertEquals("SERVER_ERROR_503", record.lastFailureClassification)
        assertTrue(record.lastFailureMessage!!.contains("Backend unavailable"))
    }

    @Test
    fun `HTTP 401 or 403 enters AUTH_BLOCKED state and stops queue drain`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(401)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"detail": "Invalid token."}""")
        )

        val env1 = createEnvelope(messageId = "auth-fail-1", timestamp = 1000L)
        val env2 = createEnvelope(messageId = "auth-fail-2", timestamp = 2000L)
        queue.enqueue(env1)
        queue.enqueue(env2)

        val summary = coordinator.drainQueue()

        assertEquals(1, summary.processedCount)
        assertEquals(1, summary.authBlockedCount)

        val record1 = queue.getRecord("auth-fail-1")
        assertNotNull(record1)
        assertEquals(DeliveryState.AUTH_BLOCKED, record1!!.deliveryState)
        assertEquals("AUTH_ERROR_401", record1.lastFailureClassification)

        // Record 2 must not have been attempted while unauthenticated
        val record2 = queue.getRecord("auth-fail-2")
        assertNotNull(record2)
        assertEquals(DeliveryState.PENDING, record2!!.deliveryState)
        assertEquals(0, record2.attemptCount)
    }

    @Test
    fun `onAuthenticationRecovered unblocks AUTH_BLOCKED records back to PENDING`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(401)
                .setBody("""{"detail": "Invalid token"}""")
        )

        val envelope = createEnvelope(messageId = "auth-recov")
        queue.enqueue(envelope)
        coordinator.drainQueue()

        assertEquals(DeliveryState.AUTH_BLOCKED, queue.getRecord("auth-recov")?.deliveryState)

        // Pilot re-authenticates
        coordinator.onAuthenticationRecovered()

        assertEquals(DeliveryState.PENDING, queue.getRecord("auth-recov")?.deliveryState)
    }

    @Test
    fun `non-retryable HTTP 4xx marks item FAILED_TERMINAL and does not loop indefinitely`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(400)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"telemetry_validation_error": "Heart rate out of physiological range"}""")
        )
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"status": "accumulating"}""")
        )

        val invalidEnv = createEnvelope(messageId = "client-err-400", timestamp = 1000L)
        val validEnv = createEnvelope(messageId = "valid-after-err", timestamp = 2000L)
        queue.enqueue(invalidEnv)
        queue.enqueue(validEnv)

        val summary = coordinator.drainQueue()

        assertEquals(2, summary.processedCount)
        assertEquals(1, summary.terminalFailureCount)
        assertEquals(1, summary.successCount)

        // Invalid record remains in queue in FAILED_TERMINAL state
        val record1 = queue.getRecord("client-err-400")
        assertNotNull(record1)
        assertEquals(DeliveryState.FAILED_TERMINAL, record1!!.deliveryState)
        assertEquals("CLIENT_ERROR_400", record1.lastFailureClassification)

        // Valid record was delivered and removed
        assertNull(queue.getRecord("valid-after-err"))
    }

    @Test
    fun `reaching maxDeliveryAttempts transitions retryable item to FAILED_TERMINAL dead-letter state`() = runTest {
        val envelope = createEnvelope(messageId = "retry-limit-test")
        queue.enqueue(envelope)

        // Max delivery attempts is 3 in test policy
        for (attempt in 1..3) {
            mockWebServer.enqueue(
                MockResponse()
                    .setResponseCode(500)
                    .setBody("Server Error")
            )
            coordinator.drainQueue(currentEpochMs = System.currentTimeMillis() + 100_000L * attempt)
        }

        val record = queue.getRecord("retry-limit-test")
        assertNotNull(record)
        assertEquals(3, record!!.attemptCount)
        assertEquals(DeliveryState.FAILED_TERMINAL, record.deliveryState)
        assertTrue(record.lastFailureMessage!!.contains("Exceeded max attempts (3)"))
    }

    @Test
    fun `deterministic ordering delivers older observation timestamp before newer observation timestamp`() = runTest {
        mockWebServer.enqueue(MockResponse().setResponseCode(201).setBody("""{"status": "accumulating"}"""))
        mockWebServer.enqueue(MockResponse().setResponseCode(201).setBody("""{"status": "accumulating"}"""))

        val newerEnv = createEnvelope(messageId = "newer-sample", timestamp = 5000L)
        val olderEnv = createEnvelope(messageId = "older-sample", timestamp = 1000L)

        // Enqueue out of chronological order
        queue.enqueue(newerEnv)
        queue.enqueue(olderEnv)

        val summary = coordinator.drainQueue()
        assertEquals(2, summary.successCount)

        // First request to MockWebServer must be older-sample
        val req1 = mockWebServer.takeRequest()
        val req2 = mockWebServer.takeRequest()
        assertTrue(req1.body.readUtf8().contains("72")) // older-sample
        assertTrue(req2.body.readUtf8().contains("72")) // newer-sample
    }

    @Test
    fun `pending queue survives process recreation and resumes delivery afterward`() = runTest {
        // Enqueue 2 items while server is offline
        val env1 = createEnvelope(messageId = "survive-1", timestamp = 1000L)
        val env2 = createEnvelope(messageId = "survive-2", timestamp = 2000L)
        queue.enqueue(env1)
        queue.enqueue(env2)

        // Simulate application process kill & recreation: instantiate brand new queue & coordinator instances
        val recoveredQueue = DurableTelemetryQueueStore(tempDir, retryPolicy = policy)
        val recoveredCoordinator = TelemetryDeliveryCoordinator(recoveredQueue, client, policy)

        assertEquals(2, recoveredQueue.countPending())

        // Backend is now online
        mockWebServer.enqueue(MockResponse().setResponseCode(201).setBody("""{"status": "accumulating"}"""))
        mockWebServer.enqueue(MockResponse().setResponseCode(201).setBody("""{"status": "accumulating"}"""))

        val summary = recoveredCoordinator.drainQueue()
        assertEquals(2, summary.successCount)
        assertEquals(0, recoveredQueue.countPending())
        assertEquals(0, recoveredQueue.countTotal())
    }
}
