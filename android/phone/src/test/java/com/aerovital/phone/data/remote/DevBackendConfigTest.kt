package com.aerovital.phone.data.remote

import android.content.Context
import android.content.SharedPreferences
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class DevBackendConfigTest {

    private lateinit var fakeContext: Context
    private lateinit var fakePrefs: FakeSharedPreferences

    @Before
    fun setup() {
        fakePrefs = FakeSharedPreferences()
        fakeContext = object : android.content.ContextWrapper(null) {
            override fun getSharedPreferences(name: String?, mode: Int): SharedPreferences {
                return fakePrefs
            }
            override fun getApplicationContext(): Context = this
        }
    }

    @Test
    fun `default backend URL is emulator 10_0_2_2 and free of hardcoded LAN addresses`() {
        assertEquals("http://10.0.2.2:8000/", DevBackendConfig.DEFAULT_EMULATOR_URL)
        assertEquals("http://127.0.0.1:8000/", DevBackendConfig.DEFAULT_ADB_REVERSE_URL)

        // Verify defaults contain no physical LAN IPs (e.g. 192.168.x.x, 10.x.x.x other than loopback)
        assertFalse(DevBackendConfig.DEFAULT_EMULATOR_URL.contains("192.168."))
        assertFalse(DevBackendConfig.DEFAULT_ADB_REVERSE_URL.contains("192.168."))

        DevBackendConfig.init(fakeContext)
        assertEquals("http://10.0.2.2:8000/", ApiClient.BASE_URL)
    }

    @Test
    fun `setBaseUrl normalizes trailing slash and updates ApiClient and preferences`() {
        DevBackendConfig.setBaseUrl(fakeContext, "http://127.0.0.1:8000")

        assertEquals("http://127.0.0.1:8000/", DevBackendConfig.getBaseUrl(fakeContext))
        assertEquals("http://127.0.0.1:8000/", ApiClient.BASE_URL)
    }

    @Test
    fun `resetToDefault restores emulator URL`() {
        DevBackendConfig.setBaseUrl(fakeContext, "http://192.168.1.100:8000/")
        assertEquals("http://192.168.1.100:8000/", ApiClient.BASE_URL)

        DevBackendConfig.resetToDefault(fakeContext)
        assertEquals("http://10.0.2.2:8000/", ApiClient.BASE_URL)
        assertEquals("http://10.0.2.2:8000/", DevBackendConfig.getBaseUrl(fakeContext))
    }

    @Test
    fun `normalizeUrl trims whitespace and ensures trailing slash`() {
        assertEquals("http://localhost:8000/", DevBackendConfig.normalizeUrl("  http://localhost:8000  "))
        assertEquals("http://localhost:8000/", DevBackendConfig.normalizeUrl("http://localhost:8000/"))
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
