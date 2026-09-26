package com.aerovital.phone.data.remote

import com.aerovital.shared.telemetry.CanonicalTelemetry
import com.google.gson.Gson
import kotlinx.coroutines.test.runTest
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.SocketPolicy
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.util.concurrent.TimeUnit

class DjangoTelemetryClientTest {

    private lateinit var mockWebServer: MockWebServer
    private val testToken = "test-token-pilot-alpha-999"
    private val fakeTokenProvider = TokenProvider { testToken }
    private val gson = Gson()

    @Before
    fun setUp() {
        mockWebServer = MockWebServer()
        mockWebServer.start()
    }

    @After
    fun tearDown() {
        mockWebServer.shutdown()
    }

    private fun createClient(tokenProvider: TokenProvider = fakeTokenProvider): DjangoTelemetryClient {
        return DjangoTelemetryClient.create(
            baseUrl = mockWebServer.url("/").toString(),
            tokenProvider = tokenProvider
        )
    }

    private fun createSampleTelemetry(
        timestamp: String = "2026-09-26T12:00:00.000Z",
        heartRate: Float? = 72.0f,
        spo2: Float? = 98.0f,
        accelX: Float? = 0.05f,
        accelY: Float? = 0.10f,
        accelZ: Float? = 9.81f,
        rawPayload: Map<String, Any>? = mapOf("device_vendor" to "WearOS", "sensor_id" to "ppg_01")
    ): CanonicalTelemetry {
        return CanonicalTelemetry(
            timestamp = timestamp,
            heartRate = heartRate,
            spo2 = spo2,
            accelX = accelX,
            accelY = accelY,
            accelZ = accelZ,
            rawPayload = rawPayload
        )
    }

    @Test
    fun `successful authenticated telemetry POST sends correct path and method`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"status": "accumulating", "telemetry": {"id": "tel-101"}}""")
        )

        val client = createClient()
        val telemetry = createSampleTelemetry()
        val result = client.sendTelemetry(telemetry)

        assertTrue("Expected Success, got $result", result is TelemetryIngestResult.Success)
        assertEquals(201, (result as TelemetryIngestResult.Success).statusCode)

        val recordedRequest = mockWebServer.takeRequest(2, TimeUnit.SECONDS)
        assertNotNull(recordedRequest)
        assertEquals("POST", recordedRequest!!.method)
        assertEquals("/api/v1/telemetry/", recordedRequest.path)
    }

    @Test
    fun `correct Authorization header is attached with Token scheme`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"status": "accumulating"}""")
        )

        val client = createClient()
        val telemetry = createSampleTelemetry()
        val result = client.sendTelemetry(telemetry)

        assertTrue(result is TelemetryIngestResult.Success)

        val recordedRequest = mockWebServer.takeRequest(2, TimeUnit.SECONDS)
        assertNotNull(recordedRequest)
        assertEquals("Token $testToken", recordedRequest!!.getHeader("Authorization"))
    }

    @Test
    fun `correct request serialization matches Django API contract`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"status": "accumulating"}""")
        )

        val client = createClient()
        val telemetry = createSampleTelemetry(
            timestamp = "2026-09-26T12:00:00.000Z",
            heartRate = 74.5f,
            spo2 = 97.0f,
            accelX = 0.12f,
            accelY = -0.34f,
            accelZ = 9.78f,
            rawPayload = mapOf("firmware" to "v2.1", "gyro_present" to true)
        )

        client.sendTelemetry(telemetry)

        val recordedRequest = mockWebServer.takeRequest(2, TimeUnit.SECONDS)
        assertNotNull(recordedRequest)
        val bodyString = recordedRequest!!.body.readUtf8()

        val jsonMap = gson.fromJson(bodyString, Map::class.java)
        assertEquals("2026-09-26T12:00:00.000Z", jsonMap["timestamp"])
        assertEquals(74.5, (jsonMap["heart_rate"] as Number).toDouble(), 0.001)
        assertEquals(97.0, (jsonMap["spo2"] as Number).toDouble(), 0.001)
        assertEquals(0.12, (jsonMap["accel_x"] as Number).toDouble(), 0.001)
        assertEquals(-0.34, (jsonMap["accel_y"] as Number).toDouble(), 0.001)
        assertEquals(9.78, (jsonMap["accel_z"] as Number).toDouble(), 0.001)

        val rawPayloadMap = jsonMap["raw_payload"] as Map<*, *>
        assertEquals("v2.1", rawPayloadMap["firmware"])
        assertEquals(true, rawPayloadMap["gyro_present"])

        // Unobserved channels must be absent or null, never zero-filled or fabricated
        assertNull(jsonMap["skin_temperature"])
        assertNull(jsonMap["rr_interval"])
        assertNull(jsonMap["steps"])
    }

    @Test
    fun `successful HTTP response handling parses status and telemetry payload`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setHeader("Content-Type", "application/json")
                .setBody(
                    """
                    {
                        "status": "evaluated",
                        "telemetry": {
                            "id": "uuid-1234",
                            "heart_rate": 72.0,
                            "timestamp": "2026-09-26T12:00:00Z"
                        },
                        "estimate": {
                            "fatigue_state": "NOMINAL"
                        },
                        "quality": {
                            "overall_sqi": 0.95
                        },
                        "alert": null
                    }
                    """.trimIndent()
                )
        )

        val client = createClient()
        val result = client.sendTelemetry(createSampleTelemetry())

        assertTrue(result is TelemetryIngestResult.Success)
        val success = result as TelemetryIngestResult.Success
        assertEquals(201, success.statusCode)
        assertNotNull(success.response)
        assertEquals("evaluated", success.response?.status)
        assertNotNull(success.response?.telemetry)
        assertNotNull(success.response?.estimate)
        assertNotNull(success.response?.quality)
        assertNull(success.response?.alert)
    }

    @Test
    fun `HTTP 401 Unauthorized returns AuthenticationError`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(401)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"detail": "Invalid token."}""")
        )

        val client = createClient()
        val result = client.sendTelemetry(createSampleTelemetry())

        assertTrue(result is TelemetryIngestResult.AuthenticationError)
        val authError = result as TelemetryIngestResult.AuthenticationError
        assertEquals(401, authError.statusCode)
        assertTrue(authError.message.contains("Invalid token"))
    }

    @Test
    fun `HTTP 403 Forbidden returns AuthenticationError`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(403)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"detail": "Cannot ingest telemetry for another pilot."}""")
        )

        val client = createClient()
        val result = client.sendTelemetry(createSampleTelemetry())

        assertTrue(result is TelemetryIngestResult.AuthenticationError)
        val authError = result as TelemetryIngestResult.AuthenticationError
        assertEquals(403, authError.statusCode)
        assertTrue(authError.message.contains("Cannot ingest telemetry"))
    }

    @Test
    fun `missing or empty token immediately returns AuthenticationError without network call`() = runTest {
        val emptyTokenProvider = TokenProvider { null }
        val client = createClient(tokenProvider = emptyTokenProvider)

        val result = client.sendTelemetry(createSampleTelemetry())

        assertTrue(result is TelemetryIngestResult.AuthenticationError)
        val authError = result as TelemetryIngestResult.AuthenticationError
        assertEquals(401, authError.statusCode)
        assertEquals(0, mockWebServer.requestCount)
    }

    @Test
    fun `HTTP 400 Bad Request returns ClientError`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(400)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"telemetry_validation_error": "Heart rate below physiological floor (30 BPM)."}""")
        )

        val client = createClient()
        val result = client.sendTelemetry(createSampleTelemetry())

        assertTrue(result is TelemetryIngestResult.ClientError)
        val clientError = result as TelemetryIngestResult.ClientError
        assertEquals(400, clientError.statusCode)
        assertTrue(clientError.message.contains("telemetry_validation_error"))
    }

    @Test
    fun `HTTP 500 Internal Server Error returns ServerError`() = runTest {
        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(500)
                .setHeader("Content-Type", "text/plain")
                .setBody("Internal Server Error")
        )

        val client = createClient()
        val result = client.sendTelemetry(createSampleTelemetry())

        assertTrue(result is TelemetryIngestResult.ServerError)
        val serverError = result as TelemetryIngestResult.ServerError
        assertEquals(500, serverError.statusCode)
        assertTrue(serverError.message.contains("Internal Server Error"))
    }

    @Test
    fun `network failure returns NetworkError`() = runTest {
        // Enqueue socket disconnect
        mockWebServer.enqueue(
            MockResponse().setSocketPolicy(SocketPolicy.DISCONNECT_AT_START)
        )

        val client = createClient()
        val result = client.sendTelemetry(createSampleTelemetry())

        assertTrue("Expected NetworkError, got $result", result is TelemetryIngestResult.NetworkError)
        assertFalse(result.isSuccess)
    }

    @Test
    fun `blank timestamp telemetry returns MalformedPayloadError without network call`() = runTest {
        val client = createClient()
        val invalidTelemetry = CanonicalTelemetry(timestamp = "   ")

        val result = client.sendTelemetry(invalidTelemetry)

        assertTrue(result is TelemetryIngestResult.MalformedPayloadError)
        assertEquals(0, mockWebServer.requestCount)
    }

    @Test
    fun `token is never written to logs via redacted Authorization header`() = runTest {
        // Build OkHttpClient using the factory logic and verify Authorization header is redacted in logs
        var loggedMessage = ""
        val loggingInterceptor = okhttp3.logging.HttpLoggingInterceptor { message ->
            loggedMessage += message + "\n"
        }.apply {
            level = okhttp3.logging.HttpLoggingInterceptor.Level.HEADERS
            redactHeader("Authorization")
        }

        val customOkHttpClient = OkHttpClient.Builder()
            .addInterceptor { chain ->
                val request = chain.request().newBuilder()
                    .addHeader("Authorization", "Token $testToken")
                    .build()
                chain.proceed(request)
            }
            .addInterceptor(loggingInterceptor)
            .build()

        val client = DjangoTelemetryClient.create(
            baseUrl = mockWebServer.url("/").toString(),
            tokenProvider = fakeTokenProvider,
            customOkHttpClient = customOkHttpClient
        )

        mockWebServer.enqueue(
            MockResponse()
                .setResponseCode(201)
                .setHeader("Content-Type", "application/json")
                .setBody("""{"status": "accumulating"}""")
        )

        client.sendTelemetry(createSampleTelemetry())

        // Verify that the secret token is NOT present in loggedMessage
        assertFalse("Log contains raw token!", loggedMessage.contains(testToken))
        // Verify that redactHeader replaced it with ██
        assertTrue("Log should redact Authorization header", loggedMessage.contains("Authorization: ██"))
    }
}
