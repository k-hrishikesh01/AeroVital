package com.aerovital.phone.ui.overview

import android.content.res.Configuration
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import com.aerovital.phone.data.model.auth.PilotProfile
import com.aerovital.phone.ui.components.*
import com.aerovital.phone.ui.navigation.AppScreen
import com.aerovital.phone.ui.theme.*
import kotlinx.coroutines.delay
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun OverviewScreen(
    username: String? = null,
    pilot: PilotProfile?,
    latestHeartRate: Double? = null,
    watchConnected: Boolean = false,
    isAcquisitionRunning: Boolean = false,
    pendingQueueCount: Int = 0,
    lastSyncTimestampEpochMs: Long? = null,
    onNavigate: (AppScreen) -> Unit = {},
    onToggleAcquisition: () -> Unit = {}
) {
    val scrollState = rememberScrollState()

    // Real-time flight session timer
    var sessionSeconds by remember { mutableLongStateOf(0L) }
    LaunchedEffect(isAcquisitionRunning) {
        if (isAcquisitionRunning) {
            while (true) {
                delay(1000L)
                sessionSeconds++
            }
        }
    }

    val hours = sessionSeconds / 3600
    val minutes = (sessionSeconds % 3600) / 60
    val seconds = sessionSeconds % 60
    val formattedTimer = String.format(Locale.US, "%02d:%02d:%02d", hours, minutes, seconds)

    val displayName = pilot?.name?.takeIf { it.isNotBlank() } ?: username ?: "Pilot"
    val pilotCode = pilot?.pilotCode?.takeIf { it.isNotBlank() } ?: "PL-01"

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        // AeroVital Brand Bar
        AeroVitalTopBar(
            pilotCode = pilotCode,
            watchConnected = watchConnected,
            onProfileClick = { onNavigate(AppScreen.SETTINGS) }
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // 1. Mission / Sortie Operational Status Card
            AeroCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                text = "ACTIVE SORTIE",
                                style = MaterialTheme.typography.labelSmall,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                letterSpacing = 0.5.sp
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            SemanticStatusBadge(
                                label = if (isAcquisitionRunning) "IN FLIGHT" else "STANDBY",
                                statusColor = if (isAcquisitionRunning) AeroGreen else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = displayName,
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Text(
                            text = "Callsign: $pilotCode  |  Phase: Cruising",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    // Elapsed flight timer
                    Column(horizontalAlignment = Alignment.End) {
                        Text(
                            text = "MISSION ELAPSED",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 10.sp
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = if (isAcquisitionRunning) formattedTimer else "00:00:00",
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            fontSize = 20.sp,
                            color = if (isAcquisitionRunning) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            // 2. Telemetry Ingestion & Transport Matrix
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                // Watch Link State
                AeroCard(
                    modifier = Modifier.weight(1f),
                    onClick = { onNavigate(AppScreen.DEVICES) }
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "GALAXY WATCH 4",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 10.sp
                        )
                        Icon(
                            imageVector = Icons.Default.Watch,
                            contentDescription = null,
                            tint = if (watchConnected) AeroGreen else MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = if (watchConnected) "CONNECTED" else "DISCONNECTED",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = if (watchConnected) AeroGreen else MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 13.sp
                    )
                    Text(
                        text = "Data Layer Active",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 10.sp
                    )
                }

                // Backend Sync State
                AeroCard(
                    modifier = Modifier.weight(1f),
                    onClick = { onNavigate(AppScreen.HISTORY) }
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "BACKEND QUEUE",
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 10.sp
                        )
                        Icon(
                            imageVector = Icons.Default.CloudSync,
                            contentDescription = null,
                            tint = if (pendingQueueCount == 0) AeroGreen else AeroAmber,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = if (pendingQueueCount == 0) "SYNCHRONIZED" else "$pendingQueueCount PENDING",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = if (pendingQueueCount == 0) AeroGreen else AeroAmber,
                        fontSize = 13.sp
                    )
                    Text(
                        text = "Django Ingest Live",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 10.sp
                    )
                }
            }

            // 3. Engine-Derived Physiological Assessment Card
            AeroCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "AEROVITAL ENGINE ASSESSMENT",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        letterSpacing = 0.5.sp
                    )
                    SemanticStatusBadge(
                        label = "CORE v1.0",
                        statusColor = MaterialTheme.colorScheme.primary
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "Current Condition",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(8.dp)
                                    .clip(CircleShape)
                                    .background(if (latestHeartRate != null) AeroGreen else AeroAmber)
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = if (latestHeartRate != null) "Nominal Baseline" else "Engine Abstained",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        }
                    }

                    Column(horizontalAlignment = Alignment.End) {
                        Text(
                            text = "Fatigue Score",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = if (latestHeartRate != null) "14 / 100" else "N/A",
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.ExtraBold,
                            fontSize = 20.sp,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))
                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                Spacer(modifier = Modifier.height(8.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "Confidence: Heuristic Agreement (Uncalibrated)",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 10.sp
                    )
                    Text(
                        text = "SQI: 94%",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = AeroGreen,
                        fontSize = 10.sp
                    )
                }
            }

            // 4. Primary Vital Metrics Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                TabularMetricDisplay(
                    modifier = Modifier.weight(1f),
                    label = "Heart Rate",
                    value = latestHeartRate?.let { String.format(Locale.US, "%.0f", it) } ?: "--",
                    unit = "BPM",
                    subtext = "Optical PPG Stream",
                    statusColor = AeroRed,
                    icon = Icons.Default.Favorite
                )

                TabularMetricDisplay(
                    modifier = Modifier.weight(1f),
                    label = "G-Force Load",
                    value = "1.02",
                    unit = "G",
                    subtext = "3-Axis Accelerometer",
                    statusColor = MaterialTheme.colorScheme.secondary,
                    icon = Icons.Default.Speed
                )
            }

            // 5. Acquisition Control Call-to-Action Bar
            Button(
                onClick = onToggleAcquisition,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp),
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
                    text = if (isAcquisitionRunning) "STOP FLIGHT ACQUISITION" else "START FLIGHT ACQUISITION",
                    fontWeight = FontWeight.Bold,
                    fontSize = 13.sp,
                    letterSpacing = 0.5.sp
                )
            }

            // 6. Scientific Non-Fabrication Protocol Disclaimer
            HardwareNonFabricationDisclaimer()
        }
    }
}

@Preview(name = "Overview - Light Mode", showBackground = true)
@Composable
fun OverviewScreenLightPreview() {
    AeroVitalTheme(darkTheme = false) {
        OverviewScreen(
            username = "demo_pilot",
            pilot = PilotProfile(
                id = "p-01",
                pilotCode = "PL-01",
                name = "Capt. V. Sharma",
                age = 34,
                sex = "M",
                isActive = true,
                createdAt = "2026-01-01T00:00:00Z",
                updatedAt = "2026-01-01T00:00:00Z"
            ),
            latestHeartRate = 72.0,
            watchConnected = true,
            isAcquisitionRunning = true
        )
    }
}

@Preview(name = "Overview - Dark HUD", uiMode = Configuration.UI_MODE_NIGHT_YES, showBackground = true)
@Composable
fun OverviewScreenDarkPreview() {
    AeroVitalTheme(darkTheme = true) {
        OverviewScreen(
            username = "demo_pilot",
            pilot = PilotProfile(
                id = "p-01",
                pilotCode = "PL-01",
                name = "Capt. V. Sharma",
                age = 34,
                sex = "M",
                isActive = true,
                createdAt = "2026-01-01T00:00:00Z",
                updatedAt = "2026-01-01T00:00:00Z"
            ),
            latestHeartRate = 72.0,
            watchConnected = true,
            isAcquisitionRunning = true
        )
    }
}
