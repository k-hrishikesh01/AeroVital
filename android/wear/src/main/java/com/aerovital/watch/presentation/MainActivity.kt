package com.aerovital.watch.presentation

import android.Manifest
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
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
import java.util.Locale

class MainActivity : ComponentActivity() {

    private lateinit var coordinator: WatchAcquisitionCoordinator

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        coordinator = WatchAcquisitionCoordinator(applicationContext)

        setContent {
            AeroVitalTheme {
                WatchDiagnosticScreen(coordinator)
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        if (::coordinator.isInitialized) {
            coordinator.stopAcquisition()
        }
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
    val lastResult by coordinator.lastTransportResult.collectAsState()
    val lastSentMsgId by coordinator.lastSentMessageId.collectAsState()

    DisposableEffect(Unit) {
        coordinator.refreshNodeStatus()
        coordinator.checkCurrentPermissionState()
        onDispose {
            // Cleaned up in Activity onDestroy
        }
    }

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
                            text = "AeroVital Diagnostics",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                }

                // 1. Permission Status
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

                // 2. Acquisition Start/Stop Action
                item {
                    val buttonColor = if (isAcquiring) Color(0xFFD32F2F) else Color(0xFF2E7D32)
                    Button(
                        onClick = {
                            if (isAcquiring) {
                                coordinator.stopAcquisition()
                            } else {
                                coordinator.startAcquisition()
                            }
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .transformedHeight(this, transformationSpec),
                        transformation = SurfaceTransformation(transformationSpec),
                        colors = ButtonDefaults.buttonColors(containerColor = buttonColor)
                    ) {
                        Text(
                            text = if (isAcquiring) "STOP ACQUISITION" else "START ACQUISITION",
                            fontWeight = FontWeight.Bold,
                            style = MaterialTheme.typography.labelMedium
                        )
                    }
                }

                // 3. Heart Rate Status & Live BPM
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

                // 6. Explicitly Unavailable Channels (Honesty per contract)
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
                                text = "Unavailable in SensorManager:",
                                style = MaterialTheme.typography.labelSmall,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "RR-Int, SpO2, Skin-Temp",
                                style = MaterialTheme.typography.labelSmall,
                                color = Color.Gray
                            )
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
                                text = "Envelopes Sent: $packetsSent",
                                style = MaterialTheme.typography.bodySmall
                            )
                            if (lastSentMsgId != null) {
                                Text(
                                    text = "Last ID: ${lastSentMsgId!!.take(8)}...",
                                    style = MaterialTheme.typography.labelSmall,
                                    fontFamily = FontFamily.Monospace
                                )
                            }
                            if (lastResult != null) {
                                Text(
                                    text = "Result: $lastResult",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = if (lastResult!!.startsWith("SUCCESS")) Color(0xFF4CAF50) else Color(0xFFF44336)
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}