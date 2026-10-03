package com.aerovital.watch.sensors

import androidx.health.services.client.MeasureCallback
import androidx.health.services.client.data.Availability
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DataTypeAvailability
import androidx.health.services.client.data.DeltaDataType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class FakeHealthMeasureProvider : HealthMeasureProvider {
    var hasPermission: Boolean = true
    var registeredCallback: MeasureCallback? = null
    var shouldFailRegistration: Boolean = false
    var unregisterCalled: Boolean = false

    override fun hasPermission(permission: String): Boolean = hasPermission

    override fun registerMeasureCallback(
        dataType: DeltaDataType<*, *>,
        callback: MeasureCallback
    ) {
        if (shouldFailRegistration) {
            throw RuntimeException("Simulated registration failure")
        }
        registeredCallback = callback
    }

    override fun unregisterMeasureCallback(
        dataType: DeltaDataType<*, *>,
        callback: MeasureCallback
    ) {
        unregisterCalled = true
        if (registeredCallback === callback) {
            registeredCallback = null
        }
    }
}

class HealthServicesHeartRateAdapterTest {

    private lateinit var fakeProvider: FakeHealthMeasureProvider
    private lateinit var adapter: HealthServicesHeartRateAdapter

    @Before
    fun setUp() {
        fakeProvider = FakeHealthMeasureProvider()
        adapter = HealthServicesHeartRateAdapter(fakeProvider)
    }

    @Test
    fun `sensorType is HEART_RATE`() {
        assertEquals(SensorType.HEART_RATE, adapter.sensorType)
    }

    @Test
    fun `checkAvailability returns AVAILABLE when permission granted`() {
        fakeProvider.hasPermission = true
        assertEquals(SensorAvailability.AVAILABLE, adapter.checkAvailability())
    }

    @Test
    fun `checkAvailability returns ERROR_NO_PERMISSION when permission missing`() {
        fakeProvider.hasPermission = false
        assertEquals(SensorAvailability.ERROR_NO_PERMISSION, adapter.checkAvailability())
    }

    @Test
    fun `start fails and notifies ERROR_NO_PERMISSION when permission missing`() {
        fakeProvider.hasPermission = false

        var notifiedAvailability: SensorAvailability? = null
        val listener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {}
            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {
                notifiedAvailability = availability
            }
        }

        val result = adapter.start(listener)
        assertFalse(result)
        assertEquals(SensorAvailability.ERROR_NO_PERMISSION, notifiedAvailability)
        assertNull(fakeProvider.registeredCallback)
    }

    @Test
    fun `start registers callback and notifies AVAILABLE when permission granted`() {
        fakeProvider.hasPermission = true

        var notifiedAvailability: SensorAvailability? = null
        val listener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {}
            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {
                notifiedAvailability = availability
            }
        }

        val result = adapter.start(listener)
        assertTrue(result)
        assertEquals(SensorAvailability.AVAILABLE, notifiedAvailability)
        assertNotNull(fakeProvider.registeredCallback)
    }

    @Test
    fun `start is idempotent when already registered`() {
        fakeProvider.hasPermission = true
        val listener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {}
            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {}
        }

        assertTrue(adapter.start(listener))
        assertTrue(adapter.start(listener))
    }

    @Test
    fun `start notifies ERROR_HARDWARE if provider throws`() {
        fakeProvider.hasPermission = true
        fakeProvider.shouldFailRegistration = true

        var notifiedAvailability: SensorAvailability? = null
        val listener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {}
            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {
                notifiedAvailability = availability
            }
        }

        val result = adapter.start(listener)
        assertFalse(result)
        assertEquals(SensorAvailability.ERROR_HARDWARE, notifiedAvailability)
    }

    @Test
    fun `stop unregisters callback`() {
        fakeProvider.hasPermission = true
        val listener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {}
            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {}
        }

        adapter.start(listener)
        assertNotNull(fakeProvider.registeredCallback)

        adapter.stop()
        assertTrue(fakeProvider.unregisterCalled)
        assertNull(fakeProvider.registeredCallback)
    }

    @Test
    fun `emitHeartRateObservation constructs and delivers SensorObservation with bpm and timestampNs`() {
        fakeProvider.hasPermission = true
        var receivedObservation: SensorObservation? = null
        val listener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {
                receivedObservation = observation
            }
            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {}
        }

        adapter.start(listener)
        adapter.emitHeartRateObservation(78.5f, 123456789000L)

        assertNotNull(receivedObservation)
        assertEquals(SensorType.HEART_RATE, receivedObservation!!.sensorType)
        assertEquals(123456789000L, receivedObservation!!.timestampNs)
        assertEquals("bpm", receivedObservation!!.unit)
        assertEquals(1, receivedObservation!!.values.size)
        assertEquals(78.5f, receivedObservation!!.values[0], 0.001f)
    }

    @Test
    fun `emitHeartRateObservation does not fail when listener is null`() {
        adapter.emitHeartRateObservation(75.0f, 1000L)
    }

    @Test
    fun `onAvailabilityChanged updates SensorListener appropriately`() {
        fakeProvider.hasPermission = true
        var latestAvailability: SensorAvailability? = null
        val listener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {}
            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {
                latestAvailability = availability
            }
        }

        adapter.start(listener)

        adapter.pushAvailabilityForTest(DataTypeAvailability.AVAILABLE)
        assertEquals(SensorAvailability.AVAILABLE, latestAvailability)

        adapter.pushAvailabilityForTest(DataTypeAvailability.ACQUIRING)
        assertEquals(SensorAvailability.AVAILABLE, latestAvailability)

        adapter.pushAvailabilityForTest(DataTypeAvailability.UNAVAILABLE_DEVICE_OFF_BODY)
        assertEquals(SensorAvailability.UNAVAILABLE, latestAvailability)
    }

    @Test
    fun `onRegistrationFailed notifies ERROR_HARDWARE`() {
        fakeProvider.hasPermission = true
        var latestAvailability: SensorAvailability? = null
        val listener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {}
            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {
                latestAvailability = availability
            }
        }

        adapter.start(listener)
        adapter.pushRegistrationFailureForTest(RuntimeException("Service died"))
        assertEquals(SensorAvailability.ERROR_HARDWARE, latestAvailability)
    }
}
