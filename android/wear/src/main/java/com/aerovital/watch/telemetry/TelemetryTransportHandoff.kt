package com.aerovital.watch.telemetry

import com.aerovital.shared.telemetry.CanonicalTelemetry
import com.aerovital.shared.transport.TransportEnvelope
import com.aerovital.shared.transport.TransportResult
import com.aerovital.watch.sensors.SensorObservation
import com.aerovital.watch.transport.WearTransportSender
import com.google.gson.Gson

/**
 * Coordinates handoff from Wear OS sensor acquisition layer to existing A2 transport sender.
 *
 * Pipeline:
 * SensorObservation -> CanonicalTelemetry -> TransportEnvelope -> WearTransportSender
 */
class TelemetryTransportHandoff(
    private val transportSender: WearTransportSender,
    private val deviceId: String,
    private val mapper: TelemetryMapper = TelemetryMapper(),
    private val gson: Gson = Gson(),
    private val clockEpochMs: () -> Long = { System.currentTimeMillis() }
) {
    private var sequenceNumber = 0L

    /**
     * Map a single observation, wrap it in a TransportEnvelope, and transmit via WearTransportSender.
     */
    suspend fun sendObservation(observation: SensorObservation): TransportResult<Unit> {
        return sendObservations(listOf(observation))
    }

    /**
     * Map a collection of observations into a single canonical telemetry sample,
     * wrap it in a TransportEnvelope, and transmit via WearTransportSender.
     */
    suspend fun sendObservations(observations: Collection<SensorObservation>): TransportResult<Unit> {
        val envelope = prepareEnvelope(observations)
        return transportSender.sendEnvelope(envelope)
    }

    /**
     * Prepare a TransportEnvelope without transmitting it (useful for inspection and testing).
     */
    fun prepareEnvelope(observations: Collection<SensorObservation>): TransportEnvelope {
        val telemetry = mapper.map(observations)
        return telemetry.toTransportEnvelope(
            deviceId = deviceId,
            timestampEpochMs = clockEpochMs(),
            sequenceNumber = ++sequenceNumber,
            gson = gson
        )
    }
}
