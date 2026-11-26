package com.aerovital.phone.ui.navigation

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AppScreenNavigationTest {

    @Test
    fun `bottomNavDestinations contains exactly the five primary mobile destinations`() {
        val destinations = AppScreen.bottomNavDestinations
        assertEquals(5, destinations.size)
        assertEquals(AppScreen.OVERVIEW, destinations[0])
        assertEquals(AppScreen.MONITORING, destinations[1])
        assertEquals(AppScreen.DEVICES, destinations[2])
        assertEquals(AppScreen.HISTORY, destinations[3])
        assertEquals(AppScreen.SETTINGS, destinations[4])
    }

    @Test
    fun `all bottom navigation destinations have titles and icons`() {
        AppScreen.bottomNavDestinations.forEach { screen ->
            assertTrue("Screen ${screen.name} must have a non-blank title", screen.title.isNotBlank())
            assertTrue("Screen ${screen.name} must have an icon defined", screen.icon != null)
            assertTrue("Screen ${screen.name} must declare isBottomNavDestination=true", screen.isBottomNavDestination)
        }
    }
}
