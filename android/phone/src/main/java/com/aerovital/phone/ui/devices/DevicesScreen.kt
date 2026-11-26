package com.aerovital.phone.ui.devices

import android.content.res.Configuration
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aerovital.phone.ui.components.*
import com.aerovital.phone.ui.theme.*
import kotlinx.coroutines.delay
import java.util.Locale

@Composable
fun DevicesScreen(
    watchConnected: Boolean = true,
    isAcquisitionRunning: Boolean = false,
    watchBatteryLevel: Int? = 82,
    totalObservationsReceived: Long = 1420L,
    onToggleAcquisition: () -> Unit = {}
) {
    val scrollState = rememberScrollState()

    var elapsedSeconds by remember { mutableLongStateOf(0L) }
    LaunchedEffect(isAcquisitionRunning) {
        if (isAcquisitionRunning) {
            while (true) {
                delay(1000L)
                elapsedSeconds++
            }
        }
    }

    val hours = elapsedSeconds / 3600
    val minutes = (elapsedSeconds % 3600) / 60
    val seconds = elapsedSeconds % 60
    val formattedDuration = String.format(Locale.US, "%02d:%02d:%02d", hours, minutes, seconds)

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        AeroVitalTopBar(
            title = "DEVICES & SENSORS",
            subtitle = "Wearable Hardware & Acquisition Management",
            watchConnected = watchConnected
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // 1. Primary Device Card: Samsung Galaxy Watch 4
            AeroCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(36.dp)
                                .clip(RoundedCornerShape(8.dp))
                                .background(MaterialTheme.colorScheme.primaryContainer),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.Watch,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onPrimaryContainer,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            Text(
                                text = "Samsung Galaxy Watch 4",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Text(
                                text = "Exynos W920  |  Wear OS 4.0",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }

                    SemanticStatusBadge(
                        label = if (watchConnected) "PAIRED & CONNECTED" else "DISCONNECTED",
                        statusColor = if (watchConnected) AeroGreen else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))
                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                Spacer(modifier = Modifier.height(10.dp))

                // Connection & Battery Details
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text(text = "TRANSPORT PROTOCOL", style = MaterialTheme.typography.labelSmall, fontSize = 9.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(text = "Wearable Data Layer (BT/Wi-Fi)", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text(text = "WATCH BATTERY", style = MaterialTheme.typography.labelSmall, fontSize = 9.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(
                            text = watchBatteryLevel?.let { "$it%" } ?: "--",
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            color = AeroGreen
                        )
                    }
                }
            }

            // 2. Acquisition Lifecycle & Service Control Card
            AeroCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "ACQUISITION SERVICE LIFECYCLE",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        letterSpacing = 0.5.sp
                    )
                    SemanticStatusBadge(
                        label = if (isAcquisitionRunning) "RUNNING" else "STOPPED",
                        statusColor = if (isAcquisitionRunning) AeroGreen else AeroRed
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text(text = "Service Type", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(text = "WearAcquisitionService (Foreground)", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text(text = "Session Duration", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(
                            text = if (isAcquisitionRunning) formattedDuration else "00:00:00",
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text(text = "Sampling Engine", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(text = "HealthServices ExerciseClient", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text(text = "Observations Ingested", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(
                            text = "$totalObservationsReceived",
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // Start/Stop Primary Control Button
                Button(
                    onClick = onToggleAcquisition,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(46.dp),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (isAcquisitionRunning) AeroRed else MaterialTheme.colorScheme.primary
                    )
                ) {
                    Icon(
                        imageVector = if (isAcquisitionRunning) Icons.Default.Stop else Icons.Default.PlayArrow,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (isAcquisitionRunning) "STOP ACQUISITION SERVICE" else "START ACQUISITION SERVICE",
                        fontWeight = FontWeight.Bold,
                        fontSize = 13.sp
                    )
                }
            }

            // 3. Sensor Capability Checklist
            AeroCard {
                Text(
                    text = "HARDWARE SENSORS & ACCESSIBILITY",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    letterSpacing = 0.5.sp
                )
                Spacer(modifier = Modifier.height(10.dp))

                SensorRow("Optical Heart Rate (PPG)", "ACTIVE (1 Hz Continuous)", AeroGreen)
                SensorRow("3-Axis Accelerometer", "ACTIVE (50 Hz Ingestion)", AeroGreen)
                SensorRow("3-Axis Gyroscope", "ACTIVE (Hardware Ready)", AeroGreen)
                SensorRow("Lead-II ECG Hardware", "UNAVAILABLE (PPG in use)", MaterialTheme.colorScheme.onSurfaceVariant)
                SensorRow("Blood Oxygen (SpO2)", "RESTRICTED (Null preserved)", MaterialTheme.colorScheme.onSurfaceVariant)
                SensorRow("Skin Temperature", "UNINSTRUMENTED (Null preserved)", MaterialTheme.colorScheme.onSurfaceVariant)
            }

            // 4. Runtime Permissions Verification
            AeroCard {
                Text(
                    text = "WEAR OS RUNTIME PERMISSIONS",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    letterSpacing = 0.5.sp
                )
                Spacer(modifier = Modifier.height(8.dp))

                PermissionRow("BODY_SENSORS", "Granted", "Optical PPG heart rate access")
                PermissionRow("BODY_SENSORS_BACKGROUND", "Granted", "Continuous acquisition with screen dimmed")
                PermissionRow("FOREGROUND_SERVICE_HEALTH", "Granted", "Prevents OS kill during long flights")
                PermissionRow("WAKE_LOCK", "Granted", "Guarantees continuous CPU telemetry processing")
            }
        }
    }
}

@Composable
private fun SensorRow(name: String, status: String, statusColor: Color) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(text = name, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Medium)
        Text(
            text = status,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Bold,
            color = statusColor,
            fontSize = 10.sp
        )
    }
}

@Composable
private fun PermissionRow(permission: String, status: String, purpose: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(text = permission, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold, fontSize = 11.sp)
            Text(text = purpose, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 10.sp)
        }
        SemanticStatusBadge(label = status, statusColor = AeroGreen)
    }
}

@Preview(name = "Devices - Light Mode", showBackground = true)
@Composable
fun DevicesScreenLightPreview() {
    AeroVitalTheme(darkTheme = false) {
        DevicesScreen(
            watchConnected = true,
            isAcquisitionRunning = true,
            watchBatteryLevel = 84
        )
    }
}

@Preview(name = "Devices - Dark HUD", uiMode = Configuration.UI_MODE_NIGHT_YES, showBackground = true)
@Composable
fun DevicesScreenDarkPreview() {
    AeroVitalTheme(darkTheme = true) {
        DevicesScreen(
            watchConnected = true,
            isAcquisitionRunning = true,
            watchBatteryLevel = 84
        )
    }
}
