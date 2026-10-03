package com.aerovital.phone.ui.diagnostic

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.aerovital.phone.data.model.auth.PilotProfile
import com.aerovital.phone.data.remote.DevBackendConfig
import com.aerovital.phone.data.remote.TelemetryIngestResult
import com.aerovital.phone.queue.QueueDiagnosticSummary
import com.aerovital.phone.telemetry.PhoneTelemetryIngestionHandler
import com.aerovital.phone.transport.WearTransportReceiver
import com.aerovital.phone.ui.theme.AeroDarkGreen
import com.aerovital.phone.ui.theme.LocalThemeIsDark
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Minimal hardware diagnostic surface on the phone for physical integration verification.
 *
 * Displays:
 * - Authenticated Pilot info (without exposing tokens or passwords)
 * - Development backend URL configuration
 * - Real-time Wearable transport packet arrival
 * - Durable queue depth, failure classifications, and delivery states
 * - Manual queue drain trigger
 */
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack

@Composable
fun PhoneDiagnosticScreen(
    username: String? = null,
    pilot: PilotProfile?,
    onLogout: () -> Unit,
    onBack: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val scrollState = rememberScrollState()

    // Handlers and State
    val ingestionHandler = remember { WearTransportReceiver.getOrInitHandler(context) }
    val transportState by WearTransportReceiver.diagnosticState.collectAsStateWithLifecycle()
    val drainSummary by ingestionHandler.deliveryCoordinator.lastDrainSummary.collectAsStateWithLifecycle()

    var queueSummary by remember { mutableStateOf(ingestionHandler.queue.getDiagnosticSummary()) }
    var isDraining by remember { mutableStateOf(false) }

    // Backend URL dev configuration
    var currentBaseUrl by remember { mutableStateOf(DevBackendConfig.getBaseUrl(context)) }
    var customUrlInput by remember { mutableStateOf(currentBaseUrl) }
    var urlUpdatedNotice by remember { mutableStateOf(false) }

    fun refreshQueue() {
        queueSummary = ingestionHandler.queue.getDiagnosticSummary()
    }

    // Refresh queue counts whenever transport packets arrive or drain occurs
    LaunchedEffect(transportState.totalReceivedEnvelopes, drainSummary) {
        refreshQueue()
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .statusBarsPadding()
            .verticalScroll(scrollState)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // App Header
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically
            ) {
                if (onBack != null) {
                    IconButton(
                        onClick = onBack,
                        modifier = Modifier.padding(end = 4.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.ArrowBack,
                            contentDescription = "Back"
                        )
                    }
                }
                Column {
                    Text(
                        text = "AeroVital Diagnostics",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "Milestone A7 Hardware Integration",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.secondary
                    )
                }
            }
            Button(
                onClick = onLogout,
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
            ) {
                Text("Logout")
            }
        }

        val isDark = LocalThemeIsDark.current
        val statusGreen = if (isDark) AeroDarkGreen else Color(0xFF2E7D32)

        // Section 1: Authentication State
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(text = "1. Authentication State", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text(text = "Pilot: ${pilot?.name ?: username ?: "Unknown"}")
                Text(text = "Pilot Code: ${pilot?.pilotCode ?: "--"}")
                Text(text = "Active Status: ${if (pilot?.isActive == true) "Active" else "Inactive"}")
                Text(
                    text = "Auth Status: Authenticated (Token safely stored in Keystore)",
                    color = statusGreen,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }

        // Section 2: Backend Development URL Configuration
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(text = "2. Development Backend URL", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text(
                    text = "Active Target: $currentBaseUrl",
                    fontFamily = FontFamily.Monospace,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Bold
                )

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = {
                        DevBackendConfig.setBaseUrl(context, DevBackendConfig.DEFAULT_ADB_REVERSE_URL)
                        currentBaseUrl = DevBackendConfig.DEFAULT_ADB_REVERSE_URL
                        customUrlInput = currentBaseUrl
                        urlUpdatedNotice = true
                    }) {
                        Text("ADB Reverse (127.0.0.1)")
                    }

                    OutlinedButton(onClick = {
                        DevBackendConfig.setBaseUrl(context, DevBackendConfig.DEFAULT_EMULATOR_URL)
                        currentBaseUrl = DevBackendConfig.DEFAULT_EMULATOR_URL
                        customUrlInput = currentBaseUrl
                        urlUpdatedNotice = true
                    }) {
                        Text("Emulator (10.0.2.2)")
                    }
                }

                OutlinedTextField(
                    value = customUrlInput,
                    onValueChange = { customUrlInput = it; urlUpdatedNotice = false },
                    label = { Text("Custom Dev URL") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )

                Button(
                    onClick = {
                        DevBackendConfig.setBaseUrl(context, customUrlInput)
                        currentBaseUrl = DevBackendConfig.getBaseUrl(context)
                        urlUpdatedNotice = true
                    },
                    modifier = Modifier.align(Alignment.End)
                ) {
                    Text("Apply Base URL")
                }

                if (urlUpdatedNotice) {
                    Text(
                        text = "Base URL updated to: $currentBaseUrl",
                        color = statusGreen,
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }

        // Section 3: Watch Transport State
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(text = "3. Watch -> Phone Transport Receiver", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Text(text = "Total Envelopes Received: ${transportState.totalReceivedEnvelopes}")
                Text(
                    text = "Last Message ID: ${transportState.lastReceivedMessageId ?: "--"}",
                    fontFamily = FontFamily.Monospace
                )
                Text(text = "Last Device ID: ${transportState.lastReceivedDeviceId ?: "--"}")
                Text(
                    text = "Last Received Timestamp: ${
                        transportState.lastReceivedTimestampEpochMs?.let {
                            SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS", Locale.US).format(Date(it))
                        } ?: "--"
                    }"
                )
                if (transportState.lastError != null) {
                    Text(
                        text = "Transport Error: ${transportState.lastError}",
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }

        // Section 4: Durable Store-and-Forward Telemetry Queue
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(text = "4. Durable Telemetry Queue (A6)", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(text = "Pending: ${queueSummary.pendingCount}", fontWeight = FontWeight.Bold)
                    Text(text = "Retryable (5xx/Net): ${queueSummary.retryableCount}")
                }
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(
                        text = "Auth Blocked (401/403): ${queueSummary.authBlockedCount}",
                        color = if (queueSummary.authBlockedCount > 0) MaterialTheme.colorScheme.error else Color.Unspecified
                    )
                    Text(
                        text = "Terminal (Dead-letter): ${queueSummary.terminalCount}",
                        color = if (queueSummary.terminalCount > 0) MaterialTheme.colorScheme.error else Color.Unspecified
                    )
                }
                Text(text = "Total Records on Disk: ${queueSummary.totalCount}")

                // Delivery Outcome
                val lastResult = drainSummary?.lastResult
                if (lastResult != null) {
                    val statusText = when (lastResult) {
                        is TelemetryIngestResult.Success -> "SUCCESS (HTTP ${lastResult.statusCode})"
                        is TelemetryIngestResult.ServerError -> "SERVER ERROR (HTTP ${lastResult.statusCode}): ${lastResult.message}"
                        is TelemetryIngestResult.AuthenticationError -> "AUTH ERROR (HTTP ${lastResult.statusCode}): ${lastResult.message}"
                        is TelemetryIngestResult.ClientError -> "CLIENT ERROR (HTTP ${lastResult.statusCode}): ${lastResult.message}"
                        is TelemetryIngestResult.NetworkError -> "NETWORK ERROR: ${lastResult.message}"
                        is TelemetryIngestResult.MalformedPayloadError -> "MALFORMED: ${lastResult.reason}"
                        is TelemetryIngestResult.UnexpectedResponseError -> "UNEXPECTED (HTTP ${lastResult.statusCode}): ${lastResult.message}"
                    }
                    val statusColor = if (lastResult is TelemetryIngestResult.Success) statusGreen else MaterialTheme.colorScheme.error
                    Text(
                        text = "Last Delivery Outcome: $statusText",
                        color = statusColor,
                        fontWeight = FontWeight.SemiBold,
                        style = MaterialTheme.typography.bodySmall
                    )
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Button(
                        onClick = {
                            coroutineScope.launch {
                                isDraining = true
                                ingestionHandler.deliveryCoordinator.drainQueue()
                                refreshQueue()
                                isDraining = false
                            }
                        },
                        enabled = !isDraining
                    ) {
                        if (isDraining) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), color = MaterialTheme.colorScheme.onPrimary)
                            Spacer(modifier = Modifier.width(8.dp))
                        }
                        Text("Drain Queue Now")
                    }

                    OutlinedButton(onClick = { refreshQueue() }) {
                        Text("Refresh Counts")
                    }
                }
            }
        }
    }
}
