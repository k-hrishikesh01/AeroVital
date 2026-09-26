package com.aerovital.shared.telemetry

import com.aerovital.shared.transport.TransportEnvelope
import com.aerovital.shared.transport.TransportResult
import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CanonicalTelemetryTest {

    private val gson = Gson()

    @Test
    fun `serialization preserves all populated fields and omits nulls by default`() {
        val telemetry = CanonicalTelemetry(
            timestamp = "2026-09-24T10:00:00Z",
            heartRate = 72.0f,
            accelX = 0.05f,
            accelY = 0.10f,
            accelZ = 0.98f,
            batteryLevel = 94.0f,
            rawPayload = mapOf("device_vendor" to "WearOS")
        )

        val json = gson.toJson(telemetry)
        assertTrue(json.contains("\"timestamp\":\"2026-09-24T10:00:00Z\""))
        assertTrue(json.contains("\"heart_rate\":72.0"))
        assertTrue(json.contains("\"accel_x\":0.05"))
        assertTrue(json.contains("\"accel_y\":0.1"))
        assertTrue(json.contains("\"accel_z\":0.98"))
        assertTrue(json.contains("\"battery_level\":94.0"))
        assertTrue(json.contains("\"raw_payload\":{\"device_vendor\":\"WearOS\"}"))

        // Unobserved channels must not appear or be zero-filled
        assertFalse(json.contains("\"spo2\""))
        assertFalse(json.contains("\"skin_temperature\""))
        assertFalse(json.contains("\"steps\""))
        assertFalse(json.contains("\"rr_interval\""))
    }

    @Test
    fun `deserialization reconstructs canonical telemetry model correctly`() {
        val json = """
            {
                "timestamp": "2026-09-24T10:05:00Z",
                "heart_rate": 68.5,
                "rr_interval": [850.0, 860.5],
                "spo2": 97.0,
                "skin_temperature": 35.8,
                "steps": 2500,
                "accel_x": 0.0,
                "accel_y": 0.1,
                "accel_z": 9.81
            }
        """.trimIndent()

        val parsed = gson.fromJson(json, CanonicalTelemetry::class.java)
        assertEquals("2026-09-24T10:05:00Z", parsed.timestamp)
        assertEquals(68.5f, parsed.heartRate)
        assertEquals(listOf(850.0f, 860.5f), parsed.rrInterval)
        assertEquals(97.0f, parsed.spo2)
        assertEquals(35.8f, parsed.skinTemperature)
        assertEquals(2500, parsed.steps)
        assertEquals(0.0f, parsed.accelX)
        assertEquals(0.1f, parsed.accelY)
        assertEquals(9.81f, parsed.accelZ)
        assertNull(parsed.batteryLevel)
        assertNull(parsed.activityLevel)
    }

    @Test
    fun `hasAcceleration returns true only when complete 3-axis triplet present`() {
        val complete = CanonicalTelemetry(
            timestamp = "2026-09-24T10:00:00Z",
            accelX = 1f, accelY = 2f, accelZ = 3f
        )
        assertTrue(complete.hasAcceleration())

        val missingZ = CanonicalTelemetry(
            timestamp = "2026-09-24T10:00:00Z",
            accelX = 1f, accelY = 2f, accelZ = null
        )
        assertFalse(missingZ.hasAcceleration())

        val allNull = CanonicalTelemetry(timestamp = "2026-09-24T10:00:00Z")
        assertFalse(allNull.hasAcceleration())
    }

    @Test
    fun `toTransportEnvelope wraps canonical telemetry into valid A2 envelope`() {
        val telemetry = CanonicalTelemetry(
            timestamp = "2026-09-24T10:00:00Z",
            heartRate = 80.0f
        )
        val currentTime = System.currentTimeMillis()
        val envelope = telemetry.toTransportEnvelope(
            deviceId = "watch-abc",
            messageId = "msg-001",
            timestampEpochMs = currentTime,
            sequenceNumber = 42L
        )

        assertEquals(TransportEnvelope.CURRENT_VERSION, envelope.version)
        assertEquals("msg-001", envelope.messageId)
        assertEquals("watch-abc", envelope.deviceId)
        assertEquals(currentTime, envelope.timestamp)
        assertEquals(TransportEnvelope.PAYLOAD_TYPE_TELEMETRY, envelope.payloadType)
        assertEquals(42L, envelope.sequenceNumber)

        // Validate envelope passes A2 validation rules
        val validation = TransportEnvelope.validate(envelope, currentTime)
        assertTrue(validation is TransportResult.Success)

        // Parse back
        val unpacked = envelope.toCanonicalTelemetry()
        assertNotNull(unpacked)
        assertEquals("2026-09-24T10:00:00Z", unpacked?.timestamp)
        assertEquals(80.0f, unpacked?.heartRate)
        assertNull(unpacked?.accelX)
    }

    @Test
    fun `fromTransportEnvelope returns null for non-telemetry envelope`() {
        val nonTelemetryEnvelope = TransportEnvelope(
            version = TransportEnvelope.CURRENT_VERSION,
            messageId = "test-msg",
            deviceId = "watch-1",
            timestamp = System.currentTimeMillis(),
            payloadType = TransportEnvelope.PAYLOAD_TYPE_TEST,
            payload = "{}"
        )

        assertNull(nonTelemetryEnvelope.toCanonicalTelemetry())
        assertNull(CanonicalTelemetry.fromTransportEnvelope(nonTelemetryEnvelope))
    }
}
