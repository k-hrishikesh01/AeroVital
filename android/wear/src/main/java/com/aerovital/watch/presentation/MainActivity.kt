package com.aerovital.watch.presentation

import android.Manifest
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.wear.compose.foundation.lazy.TransformingLazyColumn
import androidx.wear.compose.foundation.lazy.rememberTransformingLazyColumnState
import androidx.wear.compose.material3.AppScaffold
import androidx.wear.compose.material3.Button
import androidx.wear.compose.material3.ButtonDefaults
import androidx.wear.compose.material3.Card
import androidx.wear.compose.material3.CardDefaults
import androidx.wear.compose.material3.ListHeader
import androidx.wear.compose.material3.MaterialTheme
import androidx.wear.compose.material3.ScreenScaffold
import androidx.wear.compose.material3.SurfaceTransformation
import androidx.wear.compose.material3.Text
import androidx.wear.compose.material3.lazy.rememberTransformationSpec
import androidx.wear.compose.material3.lazy.transformedHeight
import com.aerovital.watch.presentation.theme.AeroVitalTheme
import com.aerovital.watch.sensors.SensorAvailability
import com.aerovital.watch.sensors.SensorPermissionState
import com.aerovital.watch.sensors.WatchAcquisitionCoordinator
import com.aerovital.watch.service.WearAcquisitionService
import java.util.Locale

class MainActivity : ComponentActivity() {

    private lateinit var coordinator: WatchAcquisitionCoordinator

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val active = WearAcquisitionService.activeCoordinator ?: WatchAcquisitionCoordinator(applicationContext).also {
            WearAcquisitionService.activeCoordinator = it
        }
        coordinator = active

        setContent {
            AeroVitalTheme {
                WatchDiagnosticScreen(coordinator)
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        // Acquisition lifecycle is owned by WearAcquisitionService;
        // do not terminate sensor acquisition when Activity is destroyed.
    }
}

@Composable
fun WatchDiagnosticScreen(coordinator: WatchAcquisitionCoordinator) {
    val context = LocalContext.current
    val listState = rememberTransformingLazyColumnState()
    val transformationSpec = rememberTransformationSpec()

    // Permission launcher
    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        coordinator.onPermissionResult(isGranted)
    }

    // Reactive states
    val isServiceActive by WearAcquisitionService.isServiceActive.collectAsState()
    val permissionState by coordinator.permissionState.collectAsState()
    val hrAvailability by coordinator.heartRateAvailability.collectAsState()
    val accelAvailability by coordinator.accelerometerAvailability.collectAsState()
    val gyroAvailability by coordinator.gyroscopeAvailability.collectAsState()

    val latestHr by coordinator.latestHeartRate.collectAsState()
    val latestAccel by coordinator.latestAccel.collectAsState()
    val latestGyro by coordinator.latestGyro.collectAsState()

    val isAcquiring by coordinator.isAcquiring.collectAsState()
    val connectedNodes by coordinator.connectedNodesCount.collectAsState()
    val packetsSent by coordinator.packetsSent.collectAsState()
    val ackedCount by coordinator.acknowledgedPacketsCount.collectAsState()
    val pendingBufferCount by coordinator.pendingBufferCount.collectAsState()
    val lastResult by coordinator.lastTransportResult.collectAsState()
    val lastSentMsgId by coordinator.lastSentMessageId.collectAsState()
    val lastAckedMsgId by coordinator.lastAckedMessageId.collectAsState()

    DisposableEffect(Unit) {
        coordinator.refreshNodeStatus()
        coordinator.checkCurrentPermissionState()
        onDispose {}
    }

    val isRunning = isAcquiring || isServiceActive

    AppScaffold {
        ScreenScaffold(scrollState = listState) { contentPadding ->
            TransformingLazyColumn(
                contentPadding = contentPadding,
                state = listState,
                modifier = Modifier.fillMaxSize()
            ) {
                // Header
                item {
                    ListHeader(
                        modifier = Modifier
                            .fillMaxWidth()
                            .transformedHeight(this, transformationSpec),
                        transformation = SurfaceTransformation(transformationSpec)
                    ) {
                        Text(
                            text = "AeroVital Flight Lab",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }

                // 1. Service Status & Permission
                item {
                    val permColor = when (permissionState) {
                        SensorPermissionState.GRANTED -> Color(0xFF4CAF50)
                        SensorPermissionState.DENIED -> Color(0xFFF44336)
                        SensorPermissionState.NOT_YET_REQUESTED -> Color(0xFFFF9800)
                    }
                    Card(
                        onClick = {
                            if (permissionState != SensorPermissionState.GRANTED) {
                                permissionLauncher.launch(Manifest.permission.BODY_SENSORS)
                            }
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .transformedHeight(this, transformationSpec),
                        transformation = SurfaceTransformation(transformationSpec),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceContainer
                        )
                    ) {
                        Column(modifier = Modifier.padding(6.dp)) {
                            Text(
                                text = "Foreground Service: ${if (isRunning) "ACTIVE (HEALTH)" else "IDLE"}",
                                color = if (isRunning) Color(0xFF4CAF50) else Color.Gray,
                                style = MaterialTheme.typography.labelSmall,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "Permission: ${permissionState.name}",
                                color = permColor,
                                style = MaterialTheme.typography.bodySmall,
                                fontWeight = FontWeight.SemiBold
                            )
                            if (permissionState != SensorPermissionState.GRANTED) {
                                Text(
                                    text = "Tap to grant BODY_SENSORS",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.primary
                                )
                            }
                        }
                    }
                }

                // 2. Acquisition Start/Stop Action (Controls WearAcquisitionService)
                item {
                    val buttonColor = if (isRunning) Color(0xFFD32F2F) else Color(0xFF2E7D32)
                    Button(
                        onClick = {
                            if (isRunning) {
                                WearAcquisitionService.stop(context)
                                coordinator.stopAcquisition()
                            } else {
                                if (permissionState != SensorPermissionState.GRANTED) {
                                    permissionLauncher.launch(Manifest.permission.BODY_SENSORS)
                                } else {
                                    WearAcquisitionService.start(context)
                                }
                            }
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .transformedHeight(this, transformationSpec),
                        transformation = SurfaceTransformation(transformationSpec),
                        colors = ButtonDefaults.buttonColors(containerColor = buttonColor)
                    ) {
                        Text(
                            text = if (isRunning) "STOP SERVICE" else "START ACQUISITION",
                            fontWeight = FontWeight.Bold,
                            style = MaterialTheme.typography.labelMedium
                        )
                    }
                }

                // 3. Heart Rate Status & Live BPM (ExerciseClient / WHS)
                item {
                    Card(
                        onClick = {},
                        modifier = Modifier
                            .fillMaxWidth()
                            .transformedHeight(this, transformationSpec),
                        transformation = SurfaceTransformation(transformationSpec)
                    ) {
                        Column(modifier = Modifier.padding(6.dp)) {
                            Text(
                                text = "Heart Rate: ${hrAvailability.name}",
                                style = MaterialTheme.typography.bodySmall,
                                fontWeight = FontWeight.SemiBold
                            )
                            Text(
                                text = if (latestHr != null) "${latestHr!!.toInt()} bpm" else "-- bpm",
                                style = MaterialTheme.typography.titleLarge,
                                fontWeight = FontWeight.Bold,
                                color = if (latestHr != null) Color(0xFFE91E63) else Color.Gray
                            )
                        }
                    }
                }

                // 4. Accelerometer Status & Readings
                item {
                    Card(
                        onClick = {},
                        modifier = Modifier
                            .fillMaxWidth()
                            .transformedHeight(this, transformationSpec),
                        transformation = SurfaceTransformation(transformationSpec)
                    ) {
                        Column(modifier = Modifier.padding(6.dp)) {
                            Text(
                                text = "Accel: ${accelAvailability.name}",
                                style = MaterialTheme.typography.bodySmall,
                                fontWeight = FontWeight.SemiBold
                            )
                            Text(
                                text = if (latestAccel != null) {
                                    String.format(
                                        Locale.US,
                                        "[%.1f, %.1f, %.1f] m/s²",
                                        latestAccel!![0],
                                        latestAccel!![1],
                                        latestAccel!![2]
                                    )
                                } else {
                                    "[--, --, --]"
                                },
                                style = MaterialTheme.typography.bodySmall,
                                fontFamily = FontFamily.Monospace
                            )
                        }
                    }
                }

                // 5. Gyroscope Status & Readings
                item {
                    Card(
                        onClick = {},
                        modifier = Modifier
                            .fillMaxWidth()
                            .transformedHeight(this, transformationSpec),
                        transformation = SurfaceTransformation(transformationSpec)
                    ) {
                        Column(modifier = Modifier.padding(6.dp)) {
                            Text(
                                text = "Gyro: ${gyroAvailability.name}",
                                style = MaterialTheme.typography.bodySmall,
                                fontWeight = FontWeight.SemiBold
                            )
                            Text(
                                text = if (latestGyro != null) {
                                    String.format(
                                        Locale.US,
                                        "[%.1f, %.1f, %.1f] rad/s",
                                        latestGyro!![0],
                                        latestGyro!![1],
                                        latestGyro!![2]
                                    )
                                } else {
                                    "[--, --, --]"
                                },
                                style = MaterialTheme.typography.bodySmall,
                                fontFamily = FontFamily.Monospace
                            )
                        }
                    }
                }

                // 6. Durable Buffer & Phone ACK Confirmation
                item {
                    Card(
                        onClick = {
                            coordinator.refreshNodeStatus()
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .transformedHeight(this, transformationSpec),
                        transformation = SurfaceTransformation(transformationSpec)
                    ) {
                        Column(modifier = Modifier.padding(6.dp)) {
                            Text(
                                text = "Durable Buffer (Crash-Safe):",
                                style = MaterialTheme.typography.labelSmall,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "Pending on Disk: $pendingBufferCount | Confirmed: $ackedCount",
                                style = MaterialTheme.typography.bodySmall,
                                color = if (pendingBufferCount == 0) Color(0xFF4CAF50) else Color(0xFFFF9800)
                            )
                            if (lastAckedMsgId != null) {
                                Text(
                                    text = "Last ACK: ${lastAckedMsgId!!.take(8)}...",
                                    style = MaterialTheme.typography.labelSmall,
                                    fontFamily = FontFamily.Monospace,
                                    color = Color(0xFF4CAF50)
                                )
                            }
                        }
                    }
                }

                // 7. Paired Phone Transport Status
                item {
                    Card(
                        onClick = { coordinator.refreshNodeStatus() },
                        modifier = Modifier
                            .fillMaxWidth()
                            .transformedHeight(this, transformationSpec),
                        transformation = SurfaceTransformation(transformationSpec)
                    ) {
                        Column(modifier = Modifier.padding(6.dp)) {
                            Text(
                                text = "Paired Phone Nodes: $connectedNodes",
                                style = MaterialTheme.typography.bodySmall,
                                fontWeight = FontWeight.SemiBold,
                                color = if (connectedNodes > 0) Color(0xFF4CAF50) else Color(0xFFFF9800)
                            )
                            Text(
                                text = "Batches Dispatched: $packetsSent",
                                style = MaterialTheme.typography.bodySmall
                            )
                            if (lastSentMsgId != null) {
                                Text(
                                    text = "Last Sent ID: ${lastSentMsgId!!.take(8)}...",
                                    style = MaterialTheme.typography.labelSmall,
                                    fontFamily = FontFamily.Monospace
                                )
                            }
                            if (lastResult != null) {
                                Text(
                                    text = "Status: $lastResult",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = if (lastResult!!.startsWith("ACK") || lastResult!!.startsWith("SENT")) Color(0xFF4CAF50) else Color(0xFFF44336)
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
