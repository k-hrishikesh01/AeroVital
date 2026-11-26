package com.aerovital.watch.sensors

import android.Manifest
import androidx.health.services.client.ExerciseUpdateCallback
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DataTypeAvailability
import androidx.health.services.client.data.ExerciseState
import androidx.health.services.client.data.ExerciseStateInfo
import androidx.health.services.client.data.ExerciseTrackedStatus
import androidx.health.services.client.data.ExerciseUpdate
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.time.Duration
import java.time.Instant

class ExerciseHeartRateAdapterTest {

    private lateinit var fakeExerciseProvider: FakeExerciseProvider
    private lateinit var fakeFallbackAdapter: FakeSensorAdapter
    private lateinit var adapter: ExerciseHeartRateAdapter

    @Before
    fun setUp() {
        fakeExerciseProvider = FakeExerciseProvider()
        fakeFallbackAdapter = FakeSensorAdapter(SensorType.HEART_RATE)
        adapter = ExerciseHeartRateAdapter(fakeExerciseProvider, fakeFallbackAdapter)
    }

    @Test
    fun `checkAvailability returns ERROR_NO_PERMISSION when BODY_SENSORS missing`() {
        fakeExerciseProvider.hasPermission = false
        val availability = adapter.checkAvailability()
        assertEquals(SensorAvailability.ERROR_NO_PERMISSION, availability)
    }

    @Test
    fun `checkAvailability falls back to fallback adapter when exercise unsupported`() {
        fakeExerciseProvider.hasPermission = true
        fakeExerciseProvider.isSupported = false

        val availability = adapter.checkAvailability()
        assertEquals(SensorAvailability.AVAILABLE, availability) // Fallback is available
    }

    @Test
    fun `start uses ExerciseClient when supported and permission granted`() {
        fakeExerciseProvider.hasPermission = true
        fakeExerciseProvider.isSupported = true

        var notifiedAvailability: SensorAvailability? = null
        val listener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {}
            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {
                notifiedAvailability = availability
            }
        }

        val started = adapter.start(listener)
        assertTrue(started)
        assertTrue(fakeExerciseProvider.isExerciseRunning)
        assertFalse("Fallback adapter should not be started when ExerciseClient succeeds", fakeFallbackAdapter.isStarted)
        assertEquals(SensorAvailability.AVAILABLE, notifiedAvailability)
    }

    @Test
    fun `start falls back to fallback adapter when ExerciseClient start fails`() {
        fakeExerciseProvider.hasPermission = true
        fakeExerciseProvider.isSupported = true
        fakeExerciseProvider.shouldFailStart = true // Simulate active exercise owned by another app

        val listener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {}
            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {}
        }

        val started = adapter.start(listener)
        assertTrue(started)
        assertFalse(fakeExerciseProvider.isExerciseRunning)
        assertTrue("Fallback adapter must be started when ExerciseClient start fails", fakeFallbackAdapter.isStarted)
    }

    @Test
    fun `stop terminates running exercise session`() {
        fakeExerciseProvider.hasPermission = true
        fakeExerciseProvider.isSupported = true

        val listener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {}
            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {}
        }

        adapter.start(listener)
        assertTrue(fakeExerciseProvider.isExerciseRunning)

        adapter.stop()
        assertFalse(fakeExerciseProvider.isExerciseRunning)
    }

    @Test
    fun `emitObservation emits valid heart rate observation to listener`() {
        var observed: SensorObservation? = null
        val listener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {
                observed = observation
            }
            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {}
        }

        adapter.start(listener)
        adapter.emitObservation(78.0f, 1500000000L)

        assertNotNull(observed)
        assertEquals(SensorType.HEART_RATE, observed?.sensorType)
        assertEquals(78.0f, observed?.values?.get(0))
        assertEquals(1500000000L, observed?.timestampNs)
    }

    @Test
    fun `availability changed updates listener`() {
        var latestAvailability: SensorAvailability? = null
        val listener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {}
            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {
                latestAvailability = availability
            }
        }

        adapter.start(listener)
        adapter.pushAvailabilityForTest(DataTypeAvailability.UNAVAILABLE)
        assertEquals(SensorAvailability.UNAVAILABLE, latestAvailability)

        adapter.pushAvailabilityForTest(DataTypeAvailability.AVAILABLE)
        assertEquals(SensorAvailability.AVAILABLE, latestAvailability)
    }
}

class FakeExerciseProvider : ExerciseProvider {
    var hasPermission: Boolean = true
    var isSupported: Boolean = true
    var shouldFailStart: Boolean = false
    var isExerciseRunning: Boolean = false
    var registeredCallback: ExerciseUpdateCallback? = null

    override fun hasPermission(permission: String): Boolean = hasPermission
    override fun isExerciseSupported(): Boolean = isSupported

    override fun startExercise(callback: ExerciseUpdateCallback): Boolean {
        if (shouldFailStart) return false
        isExerciseRunning = true
        registeredCallback = callback
        callback.onRegistered()
        return true
    }

    override fun stopExercise(callback: ExerciseUpdateCallback) {
        isExerciseRunning = false
        registeredCallback = null
    }
}
