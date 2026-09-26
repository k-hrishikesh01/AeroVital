package com.aerovital.watch.sensors

import android.content.Context
import android.content.SharedPreferences
import com.aerovital.shared.transport.TransportEnvelope
import com.aerovital.shared.transport.TransportResult
import com.aerovital.watch.telemetry.TelemetryTransportHandoff
import com.aerovital.watch.transport.MessageSender
import com.aerovital.watch.transport.NodeProvider
import com.aerovital.watch.transport.WearTransportSender
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.lang.reflect.Proxy

@OptIn(ExperimentalCoroutinesApi::class)
class WatchAcquisitionCoordinatorTest {

    private lateinit var fakeContext: Context
    private lateinit var fakePreferences: FakeSharedPreferences
    private lateinit var fakeNodeProvider: FakeNodeProvider
    private lateinit var fakeMessageSender: FakeMessageSender
    private lateinit var transportSender: WearTransportSender
    private lateinit var fakeHrAdapter: FakeSensorAdapter
    private lateinit var fakeAccelAdapter: FakeSensorAdapter
    private lateinit var fakeGyroAdapter: FakeSensorAdapter

    @Before
    fun setup() {
        fakePreferences = FakeSharedPreferences()
        fakeNodeProvider = FakeNodeProvider(listOf("phone-node-001"))
        fakeMessageSender = FakeMessageSender()
        transportSender = WearTransportSender(fakeNodeProvider, fakeMessageSender)

        fakeHrAdapter = FakeSensorAdapter(SensorType.HEART_RATE)
        fakeAccelAdapter = FakeSensorAdapter(SensorType.ACCELEROMETER)
        fakeGyroAdapter = FakeSensorAdapter(SensorType.GYROSCOPE)

        // Mock Android Context for SharedPreferences and ContentResolver
        fakeContext = createMockContext(fakePreferences)
    }

    @Test
    fun `permission result updates permission state to GRANTED and DENIED`() {
        val coordinator = WatchAcquisitionCoordinator(
            context = fakeContext,
            transportSender = transportSender,
            deviceId = "test-watch-01",
            heartRateAdapter = fakeHrAdapter,
            accelerometerAdapter = fakeAccelAdapter,
            gyroscopeAdapter = fakeGyroAdapter
        )

        coordinator.onPermissionResult(true)
        assertEquals(SensorPermissionState.GRANTED, coordinator.permissionState.value)

        coordinator.onPermissionResult(false)
        assertEquals(SensorPermissionState.DENIED, coordinator.permissionState.value)
    }

    @Test
    fun `sensor acquisition lifecycle starts and stops adapters`() = runTest {
        val coordinator = WatchAcquisitionCoordinator(
            context = fakeContext,
            transportSender = transportSender,
            deviceId = "test-watch-01",
            coroutineScope = this,
            heartRateAdapter = fakeHrAdapter,
            accelerometerAdapter = fakeAccelAdapter,
            gyroscopeAdapter = fakeGyroAdapter,
            samplingIntervalMs = 50L
        )

        assertFalse(coordinator.isAcquiring.value)
        coordinator.startAcquisition()
        assertTrue(coordinator.isAcquiring.value)
        assertTrue(fakeHrAdapter.isStarted)
        assertTrue(fakeAccelAdapter.isStarted)
        assertTrue(fakeGyroAdapter.isStarted)

        coordinator.stopAcquisition()
        assertFalse(coordinator.isAcquiring.value)
        assertFalse(fakeHrAdapter.isStarted)
        assertFalse(fakeAccelAdapter.isStarted)
        assertFalse(fakeGyroAdapter.isStarted)
    }

    @Test
    fun `observations update latest sensor states in coordinator`() = runTest {
        val coordinator = WatchAcquisitionCoordinator(
            context = fakeContext,
            transportSender = transportSender,
            deviceId = "test-watch-01",
            coroutineScope = this,
            heartRateAdapter = fakeHrAdapter,
            accelerometerAdapter = fakeAccelAdapter,
            gyroscopeAdapter = fakeGyroAdapter,
            samplingIntervalMs = 50L
        )

        coordinator.startAcquisition()

        // Push observations
        fakeHrAdapter.pushObservation(floatArrayOf(78.5f), "bpm")
        fakeAccelAdapter.pushObservation(floatArrayOf(0.1f, 9.8f, -0.2f), "m/s^2")
        fakeGyroAdapter.pushObservation(floatArrayOf(0.01f, 0.02f, 0.03f), "rad/s")

        assertEquals(78.5f, coordinator.latestHeartRate.value)
        assertNotNull(coordinator.latestAccel.value)
        assertEquals(9.8f, coordinator.latestAccel.value!![1], 0.001f)
        assertNotNull(coordinator.latestGyro.value)
        assertEquals(0.02f, coordinator.latestGyro.value!![1], 0.001f)

        coordinator.stopAcquisition()
    }

    @Test
    fun `observations are packaged and dispatched to transport on ticker interval`() = runTest {
        val coordinator = WatchAcquisitionCoordinator(
            context = fakeContext,
            transportSender = transportSender,
            deviceId = "test-watch-01",
            coroutineScope = this,
            heartRateAdapter = fakeHrAdapter,
            accelerometerAdapter = fakeAccelAdapter,
            gyroscopeAdapter = fakeGyroAdapter,
            samplingIntervalMs = 50L
        )

        coordinator.startAcquisition()

        fakeHrAdapter.pushObservation(floatArrayOf(82f), "bpm")
        fakeAccelAdapter.pushObservation(floatArrayOf(0f, 9.81f, 0f), "m/s^2")

        // Advance past sampling interval
        advanceTimeBy(60L)

        // Verify transport received the message
        assertEquals(1L, coordinator.packetsSent.value)
        assertEquals(1, fakeMessageSender.sentMessages.size)
        assertTrue(coordinator.lastTransportResult.value?.startsWith("SUCCESS") == true)

        coordinator.stopAcquisition()
    }

    @Test
    fun `node query correctly counts connected phone nodes`() = runTest {
        val coordinator = WatchAcquisitionCoordinator(
            context = fakeContext,
            transportSender = transportSender,
            deviceId = "test-watch-01",
            coroutineScope = this,
            heartRateAdapter = fakeHrAdapter,
            accelerometerAdapter = fakeAccelAdapter,
            gyroscopeAdapter = fakeGyroAdapter
        )

        coordinator.refreshNodeStatus()
        testScheduler.advanceUntilIdle()
        assertEquals(1, coordinator.connectedNodesCount.value)

        fakeNodeProvider.nodes = emptyList()
        coordinator.refreshNodeStatus()
        testScheduler.advanceUntilIdle()
        assertEquals(0, coordinator.connectedNodesCount.value)
    }

    // Test Doubles
    private fun createMockContext(prefs: SharedPreferences): Context {
        return object : android.content.ContextWrapper(null) {
            override fun getSharedPreferences(name: String?, mode: Int): SharedPreferences {
                return prefs
            }
            override fun getApplicationContext(): Context {
                return this
            }
            override fun checkPermission(permission: String, pid: Int, uid: Int): Int {
                return android.content.pm.PackageManager.PERMISSION_DENIED
            }
            override fun checkSelfPermission(permission: String): Int {
                return android.content.pm.PackageManager.PERMISSION_DENIED
            }
            override fun getContentResolver(): android.content.ContentResolver? {
                return null
            }
        }
    }
}

class FakeSensorAdapter(
    override val sensorType: SensorType
) : SensorAdapter {
    var isStarted = false
    var listener: SensorListener? = null

    override fun checkAvailability(): SensorAvailability = SensorAvailability.AVAILABLE

    override fun start(listener: SensorListener): Boolean {
        this.listener = listener
        isStarted = true
        return true
    }

    override fun stop() {
        isStarted = false
        listener = null
    }

    fun pushObservation(values: FloatArray, unit: String) {
        listener?.onObservation(
            SensorObservation(
                timestampNs = System.nanoTime(),
                sensorType = sensorType,
                values = values,
                unit = unit
            )
        )
    }
}

class FakeNodeProvider(var nodes: List<String>) : NodeProvider {
    override suspend fun getConnectedNodeIds(): List<String> = nodes
}

class FakeMessageSender : MessageSender {
    val sentMessages = mutableListOf<Triple<String, String, ByteArray>>()
    override suspend fun sendMessage(nodeId: String, path: String, data: ByteArray) {
        sentMessages.add(Triple(nodeId, path, data))
    }
}

class FakeSharedPreferences : SharedPreferences {
    private val map = mutableMapOf<String, Any?>()

    override fun getAll(): MutableMap<String, *> = map
    override fun getString(key: String?, defValue: String?): String? = map[key] as? String ?: defValue
    override fun getStringSet(key: String?, defValues: MutableSet<String>?): MutableSet<String>? = null
    override fun getInt(key: String?, defValue: Int): Int = map[key] as? Int ?: defValue
    override fun getLong(key: String?, defValue: Long): Long = map[key] as? Long ?: defValue
    override fun getFloat(key: String?, defValue: Float): Float = map[key] as? Float ?: defValue
    override fun getBoolean(key: String?, defValue: Boolean): Boolean = map[key] as? Boolean ?: defValue
    override fun contains(key: String?): Boolean = map.containsKey(key)
    override fun edit(): SharedPreferences.Editor = FakeEditor(map)
    override fun registerOnSharedPreferenceChangeListener(listener: SharedPreferences.OnSharedPreferenceChangeListener?) {}
    override fun unregisterOnSharedPreferenceChangeListener(listener: SharedPreferences.OnSharedPreferenceChangeListener?) {}

    class FakeEditor(private val target: MutableMap<String, Any?>) : SharedPreferences.Editor {
        private val staging = mutableMapOf<String, Any?>()

        override fun putString(key: String?, value: String?): SharedPreferences.Editor = apply { key?.let { staging[it] = value } }
        override fun putStringSet(key: String?, values: MutableSet<String>?): SharedPreferences.Editor = this
        override fun putInt(key: String?, value: Int): SharedPreferences.Editor = apply { key?.let { staging[it] = value } }
        override fun putLong(key: String?, value: Long): SharedPreferences.Editor = apply { key?.let { staging[it] = value } }
        override fun putFloat(key: String?, value: Float): SharedPreferences.Editor = apply { key?.let { staging[it] = value } }
        override fun putBoolean(key: String?, value: Boolean): SharedPreferences.Editor = apply { key?.let { staging[it] = value } }
        override fun remove(key: String?): SharedPreferences.Editor = apply { key?.let { staging.remove(it) } }
        override fun clear(): SharedPreferences.Editor = apply { staging.clear() }
        override fun commit(): Boolean {
            target.putAll(staging)
            return true
        }
        override fun apply() {
            target.putAll(staging)
        }
    }
}
