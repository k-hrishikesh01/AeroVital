package com.aerovital.watch.telemetry

import com.aerovital.shared.telemetry.toCanonicalTelemetry
import com.aerovital.shared.transport.TransportEnvelope
import com.aerovital.shared.transport.TransportResult
import com.aerovital.watch.sensors.SensorObservation
import com.aerovital.watch.sensors.SensorType
import com.aerovital.watch.transport.FakeMessageSender
import com.aerovital.watch.transport.FakeNodeProvider
import com.aerovital.watch.transport.WearTransportSender
import com.google.gson.Gson
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class TelemetryMapperTest {

    private val fixedIso = "2026-09-24T10:00:00Z"
    private val fixedTimeAnchor = object : TimeAnchor {
        override fun toIsoTimestamp(timestampNs: Long): String = fixedIso
    }
    private val mapper = TelemetryMapper(timeAnchor = fixedTimeAnchor)
    private val gson = Gson()

    @Test
    fun `heart-rate mapping converts observation to canonical telemetry`() {
        val obs = SensorObservation(
            timestampNs = 1234567890L,
            sensorType = SensorType.HEART_RATE,
            values = floatArrayOf(74.0f),
            unit = "bpm",
            status = 3
        )

        val telemetry = mapper.map(obs)

        assertEquals(fixedIso, telemetry.timestamp)
        assertEquals(74.0f, telemetry.heartRate)
        // All other channels must be strictly null
        assertNull(telemetry.accelX)
        assertNull(telemetry.accelY)
        assertNull(telemetry.accelZ)
        assertNull(telemetry.rrInterval)
        assertNull(telemetry.spo2)
        assertNull(telemetry.skinTemperature)
        assertNull(telemetry.steps)
        assertNull(telemetry.batteryLevel)
        assertFalse(telemetry.hasAcceleration())

        // Originating timestamp preserved in metadata
        assertEquals(1234567890L, telemetry.rawPayload?.get("originating_timestamp_ns"))
    }

    @Test
    fun `accelerometer mapping converts complete triplet to accel_x, accel_y, accel_z`() {
        val obs = SensorObservation(
            timestampNs = 1234567890L,
            sensorType = SensorType.ACCELEROMETER,
            values = floatArrayOf(0.12f, -0.98f, 9.81f),
            unit = "m/s^2"
        )

        val telemetry = mapper.map(obs)

        assertEquals(0.12f, telemetry.accelX)
        assertEquals(-0.98f, telemetry.accelY)
        assertEquals(9.81f, telemetry.accelZ)
        assertTrue(telemetry.hasAcceleration())
        assertNull(telemetry.heartRate)
    }

    @Test
    fun `accelerometer mapping rejects incomplete triplet without fabricating components`() {
        val incompleteObs = SensorObservation(
            timestampNs = 1234567890L,
            sensorType = SensorType.ACCELEROMETER,
            values = floatArrayOf(0.12f, -0.98f), // Missing Z
            unit = "m/s^2"
        )

        val telemetry = mapper.map(incompleteObs)

        assertNull(telemetry.accelX)
        assertNull(telemetry.accelY)
        assertNull(telemetry.accelZ)
        assertFalse(telemetry.hasAcceleration())
    }

    @Test
    fun `partial telemetry preserves observed channels and omits missing channels`() {
        val hrObs = SensorObservation(
            timestampNs = 1000L,
            sensorType = SensorType.HEART_RATE,
            values = floatArrayOf(82.0f),
            unit = "bpm"
        )
        val accelObs = SensorObservation(
            timestampNs = 2000L,
            sensorType = SensorType.ACCELEROMETER,
            values = floatArrayOf(0.01f, 0.02f, 0.99f),
            unit = "m/s^2"
        )

        val telemetry = mapper.map(listOf(hrObs, accelObs))

        // Populated observed channels
        assertEquals(82.0f, telemetry.heartRate)
        assertEquals(0.01f, telemetry.accelX)
        assertEquals(0.02f, telemetry.accelY)
        assertEquals(0.99f, telemetry.accelZ)
        assertTrue(telemetry.hasAcceleration())

        // Missing channels must remain strictly null (never zero-filled or fabricated)
        assertNull(telemetry.spo2)
        assertNull(telemetry.skinTemperature)
        assertNull(telemetry.rrInterval)
        assertNull(telemetry.steps)
        assertNull(telemetry.batteryLevel)
    }

    @Test
    fun `gyroscope is not fabricated into non-existent telemetry fields`() {
        val gyroObs = SensorObservation(
            timestampNs = 1234567890L,
            sensorType = SensorType.GYROSCOPE,
            values = floatArrayOf(0.01f, 0.02f, 0.03f),
            unit = "rad/s"
        )

        val telemetry = mapper.map(gyroObs)

        // Must not touch accelerometer or any standard field
        assertNull(telemetry.accelX)
        assertNull(telemetry.accelY)
        assertNull(telemetry.accelZ)
        assertNull(telemetry.heartRate)

        // Preserved in raw_payload for diagnostic provenance
        assertNotNull(telemetry.rawPayload?.get("gyroscope_raw"))
    }

    @Test
    fun `rr_interval, spo2, skin_temperature, steps only mapped when actual observation present`() {
        val rrObs = SensorObservation(1000L, SensorType.RR_INTERVAL, floatArrayOf(820f, 830f), "ms")
        val spo2Obs = SensorObservation(1000L, SensorType.SPO2, floatArrayOf(98f), "%")
        val tempObs = SensorObservation(1000L, SensorType.SKIN_TEMPERATURE, floatArrayOf(36.5f), "C")
        val stepObs = SensorObservation(1000L, SensorType.STEP_COUNTER, floatArrayOf(1250f), "steps")

        val telemetry = mapper.map(listOf(rrObs, spo2Obs, tempObs, stepObs))

        assertEquals(listOf(820f, 830f), telemetry.rrInterval)
        assertEquals(98f, telemetry.spo2)
        assertEquals(36.5f, telemetry.skinTemperature)
        assertEquals(1250, telemetry.steps)
    }

    @Test
    fun `timestamp preservation derives ISO timestamp from originating observation`() {
        // Test DefaultTimeAnchor directly with absolute epoch nanoseconds
        // 1727172000000000000L = 2024-09-24T10:00:00Z
        val anchor = DefaultTimeAnchor()
        val defaultMapper = TelemetryMapper(timeAnchor = anchor)

        val epochNanos = 1_727_172_000_000_000_000L
        val obs = SensorObservation(
            timestampNs = epochNanos,
            sensorType = SensorType.HEART_RATE,
            values = floatArrayOf(70f),
            unit = "bpm"
        )

        val telemetry = defaultMapper.map(obs)

        assertEquals("2024-09-24T10:00:00Z", telemetry.timestamp)
        assertEquals(epochNanos, telemetry.rawPayload?.get("originating_timestamp_ns"))
    }

    @Test
    fun `DefaultTimeAnchor converts realistic boot-relative nanoseconds below 1e12 correctly`() {
        val fixedEpochMs = 1_791_038_400_000L // 2026-10-03T14:40:00Z
        val fixedRealtimeNs = 500_000_000_000L // 500s uptime (< 1e12)
        val anchor = DefaultTimeAnchor(
            clockEpochMs = { fixedEpochMs },
            elapsedRealtimeNanos = { fixedRealtimeNs }
        )

        // Event occurred 2 seconds prior to current realtime
        val eventNs = 498_000_000_000L
        val iso = anchor.toIsoTimestamp(eventNs)

        assertEquals("2026-10-03T14:39:58Z", iso)
    }

    @Test
    fun `DefaultTimeAnchor converts realistic boot-relative nanoseconds above 1e12 without day-leap distortion`() {
        val fixedEpochMs = 1_791_038_400_000L // 2026-10-03T14:40:00Z
        // 30.2 trillion ns (~8.38 hours uptime, typical long-running watch)
        val fixedRealtimeNs = 30_200_000_000_000L
        val anchor = DefaultTimeAnchor(
            clockEpochMs = { fixedEpochMs },
            elapsedRealtimeNanos = { fixedRealtimeNs }
        )

        // Event occurred at exact current realtime
        val isoNow = anchor.toIsoTimestamp(fixedRealtimeNs)
        assertEquals("2026-10-03T14:40:00Z", isoNow)

        // Event occurred 5 seconds prior
        val eventNs = 30_195_000_000_000L
        val isoPast = anchor.toIsoTimestamp(eventNs)
        assertEquals("2026-10-03T14:39:55Z", isoPast)
    }

    @Test
    fun `DefaultTimeAnchor preserves consecutive 1-second sample intervals accurately`() {
        val fixedEpochMs = 1_791_038_400_000L // 2026-10-03T14:40:00Z
        val fixedRealtimeNs = 30_200_000_000_000L
        val anchor = DefaultTimeAnchor(
            clockEpochMs = { fixedEpochMs },
            elapsedRealtimeNanos = { fixedRealtimeNs }
        )

        val ts1 = 30_198_000_000_000L
        val ts2 = 30_199_000_000_000L // Exactly 1,000,000,000 ns (1.00s) later

        val iso1 = anchor.toIsoTimestamp(ts1)
        val iso2 = anchor.toIsoTimestamp(ts2)

        val instant1 = java.time.Instant.parse(iso1)
        val instant2 = java.time.Instant.parse(iso2)
        val deltaMs = java.time.Duration.between(instant1, instant2).toMillis()

        assertEquals("2026-10-03T14:39:58Z", iso1)
        assertEquals("2026-10-03T14:39:59Z", iso2)
        assertEquals(1000L, deltaMs)
    }

    @Test
    fun `serialization of mapped telemetry produces valid JSON without fabricated channels`() {
        val obs = SensorObservation(
            timestampNs = 1234567890L,
            sensorType = SensorType.HEART_RATE,
            values = floatArrayOf(75.0f),
            unit = "bpm"
        )

        val telemetry = mapper.map(obs)
        val json = gson.toJson(telemetry)

        assertTrue(json.contains("\"heart_rate\":75.0"))
        assertTrue(json.contains("\"timestamp\":\"$fixedIso\""))
        assertFalse(json.contains("\"spo2\""))
        assertFalse(json.contains("\"skin_temperature\""))
    }

    @Test
    fun `canonical telemetry wrapped in existing TransportEnvelope validates correctly`() {
        val obs = SensorObservation(
            timestampNs = 1234567890L,
            sensorType = SensorType.HEART_RATE,
            values = floatArrayOf(76.0f),
            unit = "bpm"
        )

        val telemetry = mapper.map(obs)
        val currentTime = System.currentTimeMillis()
        val envelope = telemetry.toTransportEnvelope(
            deviceId = "watch-test-01",
            messageId = "msg-telemetry-1",
            timestampEpochMs = currentTime,
            sequenceNumber = 1L
        )

        assertEquals(TransportEnvelope.CURRENT_VERSION, envelope.version)
        assertEquals("msg-telemetry-1", envelope.messageId)
        assertEquals("watch-test-01", envelope.deviceId)
        assertEquals(TransportEnvelope.PAYLOAD_TYPE_TELEMETRY, envelope.payloadType)
        assertEquals(1L, envelope.sequenceNumber)

        val result = TransportEnvelope.validate(envelope, currentTime)
        assertTrue(result is TransportResult.Success)

        val unpacked = envelope.toCanonicalTelemetry()
        assertNotNull(unpacked)
        assertEquals(76.0f, unpacked?.heartRate)
        assertEquals(fixedIso, unpacked?.timestamp)
    }

    @Test
    fun `mapper to existing transport sender integration delivers valid telemetry envelope`() = runBlocking {
        val fakeSender = FakeMessageSender()
        val fakeNodeProvider = FakeNodeProvider(listOf("phone-node-1"))
        val transportSender = WearTransportSender(
            nodeProvider = fakeNodeProvider,
            messageSender = fakeSender
        )

        val handoff = TelemetryTransportHandoff(
            transportSender = transportSender,
            deviceId = "wear-galaxy-01",
            mapper = mapper
        )

        val hrObs = SensorObservation(
            timestampNs = 1234567890L,
            sensorType = SensorType.HEART_RATE,
            values = floatArrayOf(71.5f),
            unit = "bpm"
        )

        val result = handoff.sendObservation(hrObs)
        assertTrue(result is TransportResult.Success)

        // Verify transmission through existing A2 pipeline
        assertEquals(1, fakeSender.sentMessages.size)
        val sent = fakeSender.sentMessages[0]
        assertEquals("phone-node-1", sent.nodeId)
        assertEquals("/aerovital/telemetry/v1", sent.path)

        // Verify sent bytes reconstruct valid TransportEnvelope containing CanonicalTelemetry
        val sentJson = String(sent.data, Charsets.UTF_8)
        val envelope = gson.fromJson(sentJson, TransportEnvelope::class.java)
        assertEquals(TransportEnvelope.PAYLOAD_TYPE_TELEMETRY, envelope.payloadType)
        assertEquals("wear-galaxy-01", envelope.deviceId)
        assertEquals(1L, envelope.sequenceNumber)

        val unpackedTelemetry = envelope.toCanonicalTelemetry()
        assertNotNull(unpackedTelemetry)
        assertEquals(71.5f, unpackedTelemetry?.heartRate)
        assertEquals(fixedIso, unpackedTelemetry?.timestamp)
    }
}
