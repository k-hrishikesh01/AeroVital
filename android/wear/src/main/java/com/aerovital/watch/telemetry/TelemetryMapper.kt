package com.aerovital.watch.telemetry

import com.aerovital.shared.telemetry.CanonicalTelemetry
import com.aerovital.watch.sensors.SensorObservation
import com.aerovital.watch.sensors.SensorType
import java.time.Instant
import java.time.format.DateTimeFormatter

/**
 * Strategy for converting sensor timestamps into ISO-8601 UTC timestamp strings.
 */
interface TimeAnchor {
    fun toIsoTimestamp(timestampNs: Long): String
}

/**
 * Default TimeAnchor implementation.
 *
 * Preserves the originating SensorObservation hardware timestamp without fabricating
 * or silently replacing it with wall-clock time at mapping execution.
 *
 * Handles:
 * 1. Monotonic nanoseconds since device boot (standard Android SensorEvent.timestamp).
 *    Derives event epoch time via boot offset anchor without altering true measurement time.
 * 2. Absolute epoch timestamps in nanoseconds (>= 1e18) or milliseconds (>= 1e12).
 */
class DefaultTimeAnchor(
    private val clockEpochMs: () -> Long = { System.currentTimeMillis() },
    private val elapsedRealtimeNanos: () -> Long = {
        try {
            android.os.SystemClock.elapsedRealtimeNanos()
        } catch (e: Throwable) {
            System.nanoTime()
        }
    }
) : TimeAnchor {
    override fun toIsoTimestamp(timestampNs: Long): String {
        val instant = when {
            // Absolute epoch nanoseconds (e.g. >= 1e18 ~ year 2001+)
            timestampNs >= 1_000_000_000_000_000_000L -> {
                Instant.ofEpochSecond(timestampNs / 1_000_000_000L, timestampNs % 1_000_000_000L)
            }
            // Absolute epoch milliseconds
            timestampNs >= 1_000_000_000_000L -> {
                Instant.ofEpochMilli(timestampNs)
            }
            // Monotonic nanoseconds since boot (standard Android SensorEvent.timestamp)
            else -> {
                val currentRealtime = elapsedRealtimeNanos()
                val currentWallClock = clockEpochMs()
                val deltaNanos = currentRealtime - timestampNs
                val eventEpochMs = currentWallClock - (deltaNanos / 1_000_000L)
                Instant.ofEpochMilli(eventEpochMs)
            }
        }
        return DateTimeFormatter.ISO_INSTANT.format(instant)
    }
}

/**
 * Maps typed SensorObservation instances from A3 into canonical AeroVital telemetry.
 *
 * Conforms to the following principles:
 * - Maps HEART_RATE -> heart_rate
 * - Maps ACCELEROMETER -> accel_x, accel_y, accel_z (complete triplet only)
 * - GYROSCOPE is never fabricated into non-existent backend fields; kept in raw_payload
 * - Only maps RR_INTERVAL, SPO2, SKIN_TEMPERATURE, STEPS if real observations exist
 * - Preserves originating sensor timestamps faithfully
 * - Supports partial telemetry (unobserved channels are strictly null, never zero-filled or fabricated)
 */
class TelemetryMapper(
    private val timeAnchor: TimeAnchor = DefaultTimeAnchor()
) {
    /**
     * Map a single sensor observation to canonical telemetry.
     */
    fun map(observation: SensorObservation): CanonicalTelemetry {
        return map(listOf(observation))
    }

    /**
     * Map a collection of sensor observations into a single canonical telemetry sample.
     */
    fun map(observations: Collection<SensorObservation>): CanonicalTelemetry {
        require(observations.isNotEmpty()) { "Cannot map empty observations" }

        val latestObs = observations.maxByOrNull { it.timestampNs } ?: observations.first()
        val isoTimestamp = timeAnchor.toIsoTimestamp(latestObs.timestampNs)

        var heartRate: Float? = null
        var rrInterval: List<Float>? = null
        var spo2: Float? = null
        var skinTemperature: Float? = null
        var activityLevel: Any? = null
        var steps: Int? = null
        var accelX: Float? = null
        var accelY: Float? = null
        var accelZ: Float? = null
        var batteryLevel: Float? = null

        val rawMetadata = mutableMapOf<String, Any>()
        rawMetadata["originating_timestamp_ns"] = latestObs.timestampNs

        for (obs in observations) {
            when (obs.sensorType) {
                SensorType.HEART_RATE -> {
                    if (obs.values.isNotEmpty()) {
                        heartRate = obs.values[0]
                    }
                }
                SensorType.ACCELEROMETER -> {
                    // Only map if complete 3-axis triplet is provided
                    if (obs.values.size >= 3) {
                        accelX = obs.values[0]
                        accelY = obs.values[1]
                        accelZ = obs.values[2]
                    }
                }
                SensorType.RR_INTERVAL -> {
                    if (obs.values.isNotEmpty()) {
                        rrInterval = obs.values.toList()
                    }
                }
                SensorType.SPO2 -> {
                    if (obs.values.isNotEmpty()) {
                        spo2 = obs.values[0]
                    }
                }
                SensorType.SKIN_TEMPERATURE -> {
                    if (obs.values.isNotEmpty()) {
                        skinTemperature = obs.values[0]
                    }
                }
                SensorType.STEP_COUNTER -> {
                    if (obs.values.isNotEmpty()) {
                        steps = obs.values[0].toInt()
                    }
                }
                SensorType.GYROSCOPE -> {
                    // GYROSCOPE has no corresponding top-level field in AeroVital contract.
                    // Preserve in raw_payload for diagnostic provenance without fabricating schema fields.
                    rawMetadata["gyroscope_raw"] = obs.values.toList()
                }
            }
        }

        return CanonicalTelemetry(
            timestamp = isoTimestamp,
            heartRate = heartRate,
            rrInterval = rrInterval,
            spo2 = spo2,
            skinTemperature = skinTemperature,
            activityLevel = activityLevel,
            steps = steps,
            accelX = accelX,
            accelY = accelY,
            accelZ = accelZ,
            batteryLevel = batteryLevel,
            rawPayload = if (rawMetadata.isNotEmpty()) rawMetadata else null
        )
    }
}
