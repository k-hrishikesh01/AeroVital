package com.aerovital.phone.ui.theme

import android.content.Context
import android.content.SharedPreferences
import com.aerovital.phone.data.remote.FakeSharedPreferences
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class ThemePreferencesTest {

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
    fun `default dark mode is false (light mode default)`() {
        assertFalse(ThemePreferences.isDarkMode(fakeContext))
    }

    @Test
    fun `default theme mode is SYSTEM`() {
        assertEquals(ThemeMode.SYSTEM, ThemePreferences.getThemeMode(fakeContext))
    }

    @Test
    fun `setThemeMode persists SYSTEM, LIGHT, and DARK correctly`() {
        ThemePreferences.setThemeMode(fakeContext, ThemeMode.DARK)
        assertEquals(ThemeMode.DARK, ThemePreferences.getThemeMode(fakeContext))
        assertTrue(ThemePreferences.isDarkMode(fakeContext))

        ThemePreferences.setThemeMode(fakeContext, ThemeMode.LIGHT)
        assertEquals(ThemeMode.LIGHT, ThemePreferences.getThemeMode(fakeContext))
        assertFalse(ThemePreferences.isDarkMode(fakeContext))

        ThemePreferences.setThemeMode(fakeContext, ThemeMode.SYSTEM)
        assertEquals(ThemeMode.SYSTEM, ThemePreferences.getThemeMode(fakeContext))
    }

    @Test
    fun `setDarkMode true persists and is retrieved as true`() {
        ThemePreferences.setDarkMode(fakeContext, true)
        assertTrue(ThemePreferences.isDarkMode(fakeContext))
    }

    @Test
    fun `setDarkMode false persists and is retrieved as false`() {
        ThemePreferences.setDarkMode(fakeContext, true)
        assertTrue(ThemePreferences.isDarkMode(fakeContext))

        ThemePreferences.setDarkMode(fakeContext, false)
        assertFalse(ThemePreferences.isDarkMode(fakeContext))
    }
}
