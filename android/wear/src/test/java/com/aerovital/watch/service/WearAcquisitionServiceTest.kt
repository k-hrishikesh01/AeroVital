package com.aerovital.watch.service

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class WearAcquisitionServiceTest {

    @Test
    fun `service constants conform to AeroVital Wear OS foreground service contract`() {
        assertEquals("com.aerovital.watch.action.START_ACQUISITION", WearAcquisitionService.ACTION_START)
        assertEquals("com.aerovital.watch.action.STOP_ACQUISITION", WearAcquisitionService.ACTION_STOP)
        assertEquals(1001, WearAcquisitionService.NOTIFICATION_ID)
        assertEquals("aerovital_wear_acquisition", WearAcquisitionService.CHANNEL_ID)
    }

    @Test
    fun `isServiceActive state flow reflects initial idle state`() {
        assertFalse(WearAcquisitionService.isServiceActive.value)
    }
}
