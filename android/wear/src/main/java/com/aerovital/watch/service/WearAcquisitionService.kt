package com.aerovital.watch.service

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.aerovital.watch.R
import com.aerovital.watch.presentation.MainActivity
import com.aerovital.watch.sensors.WatchAcquisitionCoordinator
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * Dedicated Foreground Service managing the Wear OS physiological acquisition lifecycle.
 *
 * Runs continuously in the background independently of MainActivity,
 * holding a PARTIAL_WAKE_LOCK and foreground service type HEALTH (Android 14+).
 * Displays a persistent notification with live flight metrics and explicit Stop control.
 */
class WearAcquisitionService : Service() {

    private val serviceScope = CoroutineScope(Dispatchers.Main + Job())
    private var wakeLock: PowerManager.WakeLock? = null
    private var notificationUpdateJob: Job? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        if (activeCoordinator == null) {
            activeCoordinator = WatchAcquisitionCoordinator(applicationContext)
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                Log.i(TAG, "WearAcquisitionService received ACTION_STOP")
                stopAcquisition()
                return START_NOT_STICKY
            }
            ACTION_START, null -> {
                Log.i(TAG, "WearAcquisitionService received ACTION_START")
                startAcquisition()
                return START_STICKY
            }
            else -> {
                return START_NOT_STICKY
            }
        }
    }

    private fun startAcquisition() {
        // 1. Verify runtime permission
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.BODY_SENSORS) != PackageManager.PERMISSION_GRANTED) {
            Log.e(TAG, "Cannot start acquisition service: BODY_SENSORS permission not granted")
            stopSelf()
            return
        }

        // 2. Acquire partial wake lock to prevent watch CPU sleeping when display turns off
        acquireWakeLock()

        // 3. Start foreground notification
        val notification = buildNotification("Starting physiological sensors...")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_HEALTH)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }

        // 4. Start sensor coordinator
        val coordinator = activeCoordinator ?: WatchAcquisitionCoordinator(applicationContext).also {
            activeCoordinator = it
        }
        coordinator.startAcquisition()
        _isServiceActive.value = true

        // 5. Periodic notification updater with live flight telemetry status
        notificationUpdateJob?.cancel()
        notificationUpdateJob = serviceScope.launch {
            while (isActive) {
                delay(3000L)
                val hr = coordinator.latestHeartRate.value?.let { "${it.toInt()} BPM" } ?: "Acquiring..."
                val pending = coordinator.pendingBufferCount.value
                val statusText = "HR: $hr | Buffer: $pending pending"
                val updatedNotification = buildNotification(statusText)
                val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
                notificationManager.notify(NOTIFICATION_ID, updatedNotification)
            }
        }
    }

    private fun stopAcquisition() {
        notificationUpdateJob?.cancel()
        notificationUpdateJob = null

        activeCoordinator?.stopAcquisition()
        _isServiceActive.value = false

        releaseWakeLock()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            stopForeground(STOP_FOREGROUND_REMOVE)
        } else {
            @Suppress("DEPRECATION")
            stopForeground(true)
        }
        stopSelf()
    }

    private fun acquireWakeLock() {
        if (wakeLock == null) {
            val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
            wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, WAKE_LOCK_TAG).apply {
                setReferenceCounted(false)
            }
        }
        wakeLock?.let {
            if (!it.isHeld) {
                it.acquire(4 * 60 * 60 * 1000L) // Bounded 4-hour safety max
                Log.i(TAG, "Acquired partial wake lock for background acquisition")
            }
        }
    }

    private fun releaseWakeLock() {
        wakeLock?.let {
            if (it.isHeld) {
                it.release()
                Log.i(TAG, "Released partial wake lock")
            }
        }
        wakeLock = null
    }

    private fun buildNotification(contentText: String): Notification {
        val launchIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val launchPendingIntent = PendingIntent.getActivity(
            this,
            0,
            launchIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val stopIntent = Intent(this, WearAcquisitionService::class.java).apply {
            action = ACTION_STOP
        }
        val stopPendingIntent = PendingIntent.getService(
            this,
            1,
            stopIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("AeroVital Flight Telemetry")
            .setContentText(contentText)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setOngoing(true)
            .setContentIntent(launchPendingIntent)
            .addAction(android.R.drawable.ic_media_pause, "Stop", stopPendingIntent)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "AeroVital Flight Telemetry",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Shows real-time status of continuous flight telemetry acquisition"
                setShowBadge(false)
            }
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        stopAcquisition()
        Log.i(TAG, "WearAcquisitionService destroyed")
    }

    companion object {
        const val TAG = "WearAcquisitionService"
        const val ACTION_START = "com.aerovital.watch.action.START_ACQUISITION"
        const val ACTION_STOP = "com.aerovital.watch.action.STOP_ACQUISITION"
        const val NOTIFICATION_ID = 1001
        const val CHANNEL_ID = "aerovital_wear_acquisition"
        private const val WAKE_LOCK_TAG = "aerovital:acquisition_wakelock"

        @Volatile
        var activeCoordinator: WatchAcquisitionCoordinator? = null

        private val _isServiceActive = MutableStateFlow(false)
        val isServiceActive: StateFlow<Boolean> = _isServiceActive.asStateFlow()

        fun start(context: Context) {
            val intent = Intent(context, WearAcquisitionService::class.java).apply {
                action = ACTION_START
            }
            ContextCompat.startForegroundService(context, intent)
        }

        fun stop(context: Context) {
            val intent = Intent(context, WearAcquisitionService::class.java).apply {
                action = ACTION_STOP
            }
            context.startService(intent)
        }
    }
}
