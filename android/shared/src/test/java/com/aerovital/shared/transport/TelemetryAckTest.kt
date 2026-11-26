package com.aerovital.shared.transport

import com.aerovital.shared.telemetry.CanonicalTelemetry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class TelemetryAckTest {

    @Test
    fun `TelemetryAck serializes and deserializes correctly`() {
        val ack = TelemetryAck(
            messageId = "msg-101",
            batchId = "batch-55",
            sequenceNumber = 42L,
            status = TelemetryAck.STATUS_STORED,
            timestamp = 1700000000000L
        )

        val json = ack.toJson()
        val parsed = TelemetryAck.fromJson(json)

        assertNotNull(parsed)
        assertEquals("msg-101", parsed?.messageId)
        assertEquals("batch-55", parsed?.batchId)
        assertEquals(42L, parsed?.sequenceNumber)
        assertEquals(TelemetryAck.STATUS_STORED, parsed?.status)
        assertEquals(1700000000000L, parsed?.timestamp)
    }

    @Test
    fun `TelemetryBatch serializes and deserializes correctly`() {
        val samples = listOf(
            CanonicalTelemetry(timestamp = "2026-11-25T12:00:01Z", heartRate = 72f),
            CanonicalTelemetry(timestamp = "2026-11-25T12:00:02Z", heartRate = 74f)
        )
        val batch = TelemetryBatch(
            batchId = "batch-abc",
            samples = samples,
            batchTimestamp = 1700000001000L
        )

        val json = batch.toJson()
        val parsed = TelemetryBatch.fromJson(json)

        assertNotNull(parsed)
        assertEquals("batch-abc", parsed?.batchId)
        assertEquals(2, parsed?.samples?.size)
        assertEquals(72f, parsed?.samples?.get(0)?.heartRate)
        assertEquals(74f, parsed?.samples?.get(1)?.heartRate)
    }

    @Test
    fun `TransportEnvelope accepts batch payload type`() {
        val env = TransportEnvelope(
            version = 1,
            messageId = "env-batch-1",
            deviceId = "watch-01",
            timestamp = 1700000000000L,
            payloadType = TransportEnvelope.PAYLOAD_TYPE_TELEMETRY_BATCH,
            payload = "{}",
            batchId = "batch-1",
            sequenceNumber = 1L
        )
        val result = TransportEnvelope.validate(env, 1700000000000L)
        assertTrue(result is TransportResult.Success)
    }
}
