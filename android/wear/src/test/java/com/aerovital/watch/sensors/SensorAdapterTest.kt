package com.aerovital.watch.sensors

import android.hardware.SensorEventListener
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class SensorAdapterTest {

    private lateinit var fakeProvider: FakeSensorProvider

    @Before
    fun setup() {
        fakeProvider = FakeSensorProvider()
    }

    @Test
    fun `permission state exposes not yet requested state`() {
        fakeProvider.hasPermission = false
        fakeProvider.permissionWasRequested = false

        assertEquals(
            SensorPermissionState.NOT_YET_REQUESTED,
            fakeProvider.permissionState("android.permission.BODY_SENSORS")
        )
    }

    @Test
    fun `permission state exposes granted and denied states`() {
        fakeProvider.hasPermission = true
        assertEquals(SensorPermissionState.GRANTED, fakeProvider.permissionState("android.permission.BODY_SENSORS"))

        fakeProvider.hasPermission = false
        fakeProvider.permissionWasRequested = true
        assertEquals(SensorPermissionState.DENIED, fakeProvider.permissionState("android.permission.BODY_SENSORS"))
    }

    @Test
    fun `sensor available when permission granted and hardware present`() {
        val adapter = AndroidSensorAdapter(
            sensorProvider = fakeProvider,
            sensorType = SensorType.HEART_RATE,
            androidSensorType = 21, // TYPE_HEART_RATE
            unit = "bpm",
            permission = "android.permission.BODY_SENSORS"
        )
        fakeProvider.hasPermission = true
        fakeProvider.hasHardware = true

        assertEquals(SensorAvailability.AVAILABLE, adapter.checkAvailability())
    }

    @Test
    fun `sensor unavailable when permission missing`() {
        val adapter = AndroidSensorAdapter(
            sensorProvider = fakeProvider,
            sensorType = SensorType.HEART_RATE,
            androidSensorType = 21,
            unit = "bpm",
            permission = "android.permission.BODY_SENSORS"
        )
        fakeProvider.hasPermission = false
        fakeProvider.hasHardware = true

        assertEquals(SensorAvailability.ERROR_NO_PERMISSION, adapter.checkAvailability())
    }

    @Test
    fun `sensor unavailable when hardware missing`() {
        val adapter = AndroidSensorAdapter(
            sensorProvider = fakeProvider,
            sensorType = SensorType.HEART_RATE,
            androidSensorType = 21,
            unit = "bpm",
            permission = "android.permission.BODY_SENSORS"
        )
        fakeProvider.hasPermission = true
        fakeProvider.hasHardware = false

        assertEquals(SensorAvailability.UNAVAILABLE, adapter.checkAvailability())
    }

    @Test
    fun `start fails if unavailable`() {
        val adapter = AndroidSensorAdapter(
            sensorProvider = fakeProvider,
            sensorType = SensorType.HEART_RATE,
            androidSensorType = 21,
            unit = "bpm",
            permission = "android.permission.BODY_SENSORS"
        )
        fakeProvider.hasPermission = false
        fakeProvider.hasHardware = true

        var notifiedAvailability: SensorAvailability? = null
        val listener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {}
            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {
                notifiedAvailability = availability
            }
        }

        val started = adapter.start(listener)
        assertFalse(started)
        assertEquals(SensorAvailability.ERROR_NO_PERMISSION, notifiedAvailability)
    }

    @Test
    fun `start succeeds and propagates observations`() {
        val adapter = AndroidSensorAdapter(
            sensorProvider = fakeProvider,
            sensorType = SensorType.ACCELEROMETER,
            androidSensorType = 1, // TYPE_ACCELEROMETER
            unit = "m/s^2",
            permission = null
        )
        fakeProvider.hasHardware = true

        var notifiedAvailability: SensorAvailability? = null
        var lastObservation: SensorObservation? = null

        val listener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {
                lastObservation = observation
            }
            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {
                notifiedAvailability = availability
            }
        }

        val started = adapter.start(listener)
        assertTrue(started)
        assertEquals(SensorAvailability.AVAILABLE, notifiedAvailability)
        assertTrue(fakeProvider.isRegistered)

        // Mock a sensor event
        val timestamp = 1234567890L
        val values = floatArrayOf(9.8f, 0.1f, 0.2f)
        adapter.pushMockObservation(timestamp, values, 3)

        assertEquals(SensorType.ACCELEROMETER, lastObservation?.sensorType)
        assertEquals(timestamp, lastObservation?.timestampNs)
        assertEquals("m/s^2", lastObservation?.unit)
        assertEquals(9.8f, lastObservation?.values?.get(0))
        assertEquals(3, lastObservation?.status)

        // Stop
        adapter.stop()
        assertFalse(fakeProvider.isRegistered)
    }

    @Test
    fun `UnavailableSensorAdapter behaves correctly`() {
        val adapter = UnavailableSensorAdapter(SensorType.SPO2)
        assertEquals(SensorAvailability.UNAVAILABLE, adapter.checkAvailability())

        var notifiedAvailability: SensorAvailability? = null
        val listener = object : SensorListener {
            override fun onObservation(observation: SensorObservation) {}
            override fun onAvailabilityChanged(sensorType: SensorType, availability: SensorAvailability) {
                notifiedAvailability = availability
            }
        }

        val started = adapter.start(listener)
        assertFalse(started)
        assertEquals(SensorAvailability.UNAVAILABLE, notifiedAvailability)
    }
}

class FakeSensorProvider : SensorProvider {
    var hasPermission = true
    var hasHardware = true
    var permissionWasRequested = false
    var isRegistered = false

    override fun hasPermission(permission: String): Boolean = hasPermission
    override fun permissionState(permission: String): SensorPermissionState =
        when {
            hasPermission -> SensorPermissionState.GRANTED
            permissionWasRequested -> SensorPermissionState.DENIED
            else -> SensorPermissionState.NOT_YET_REQUESTED
        }
    override fun hasSensor(type: Int): Boolean = hasHardware

    override fun registerListener(listener: SensorEventListener, type: Int): Boolean {
        if (!hasHardware) return false
        isRegistered = true
        return true
    }

    override fun unregisterListener(listener: SensorEventListener) {
        isRegistered = false
    }
}
