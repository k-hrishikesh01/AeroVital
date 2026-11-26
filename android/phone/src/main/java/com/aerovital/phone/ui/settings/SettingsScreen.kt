package com.aerovital.phone.ui.settings

import android.content.res.Configuration
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aerovital.phone.data.model.auth.PilotProfile
import com.aerovital.phone.data.remote.DevBackendConfig
import com.aerovital.phone.ui.components.*
import com.aerovital.phone.ui.theme.*

@Composable
fun SettingsScreen(
    username: String? = null,
    pilot: PilotProfile?,
    currentThemeMode: ThemeMode = ThemeMode.SYSTEM,
    onThemeModeChanged: (ThemeMode) -> Unit = {},
    // Legacy support
    isDarkMode: Boolean = false,
    onDarkModeChanged: ((Boolean) -> Unit)? = null,
    onBack: (() -> Unit)? = null,
    onDiagnosticsClick: (() -> Unit)? = null,
    onLogoutClick: () -> Unit = {}
) {
    val context = LocalContext.current
    val scrollState = rememberScrollState()

    val displayName = pilot?.name?.takeIf { it.isNotBlank() } ?: username ?: "Pilot"
    val pilotCode = pilot?.pilotCode?.takeIf { it.isNotBlank() } ?: "PL-01"

    // Dev backend config
    var currentBaseUrl by remember { mutableStateOf(DevBackendConfig.getBaseUrl(context)) }
    var customUrlInput by remember { mutableStateOf(currentBaseUrl) }
    var urlUpdatedNotice by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        AeroVitalTopBar(
            title = "SETTINGS & PROFILE",
            subtitle = "Aviation Account & System Configuration",
            pilotCode = pilotCode
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // 1. Appearance / Theme Preference Selector
            AeroCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "APPEARANCE MODE",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        letterSpacing = 0.5.sp
                    )
                    SemanticStatusBadge(
                        label = currentThemeMode.name,
                        statusColor = MaterialTheme.colorScheme.primary
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    ThemeOptionButton(
                        modifier = Modifier.weight(1f),
                        label = "System",
                        selected = currentThemeMode == ThemeMode.SYSTEM,
                        icon = Icons.Default.BrightnessAuto,
                        onClick = {
                            onThemeModeChanged(ThemeMode.SYSTEM)
                            onDarkModeChanged?.invoke(false)
                        }
                    )
                    ThemeOptionButton(
                        modifier = Modifier.weight(1f),
                        label = "Light",
                        selected = currentThemeMode == ThemeMode.LIGHT,
                        icon = Icons.Default.LightMode,
                        onClick = {
                            onThemeModeChanged(ThemeMode.LIGHT)
                            onDarkModeChanged?.invoke(false)
                        }
                    )
                    ThemeOptionButton(
                        modifier = Modifier.weight(1f),
                        label = "Dark HUD",
                        selected = currentThemeMode == ThemeMode.DARK,
                        icon = Icons.Default.DarkMode,
                        onClick = {
                            onThemeModeChanged(ThemeMode.DARK)
                            onDarkModeChanged?.invoke(true)
                        }
                    )
                }
            }

            // 2. Pilot Profile Information
            AeroCard {
                Text(
                    text = "PILOT CREDENTIALS",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    letterSpacing = 0.5.sp
                )
                Spacer(modifier = Modifier.height(10.dp))

                ProfileFieldRow("Name", displayName)
                ProfileFieldRow("Pilot Code / Callsign", pilotCode)
                ProfileFieldRow("Role", "Flight Test Crew / Research Operator")
                ProfileFieldRow("Operational Status", if (pilot?.isActive != false) "Active Flight Status" else "Restricted")
            }

            // 3. Central Production Backend Configuration
            AeroCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "DJANGO REST BACKEND CONNECTION",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        letterSpacing = 0.5.sp
                    )
                    Text(
                        text = if (currentBaseUrl.contains("onrender.com")) "PRODUCTION API" else "DEV OVERRIDE",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = if (currentBaseUrl.contains("onrender.com")) AeroSemanticGreen else AeroSemanticAmber,
                        fontSize = 9.sp
                    )
                }

                Spacer(modifier = Modifier.height(8.dp))

                OutlinedTextField(
                    value = customUrlInput,
                    onValueChange = {
                        customUrlInput = it
                        urlUpdatedNotice = false
                    },
                    label = { Text("Base URL", fontSize = 11.sp) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    textStyle = androidx.compose.ui.text.TextStyle(
                        fontFamily = FontFamily.Monospace,
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurface
                    ),
                    shape = RoundedCornerShape(8.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = MaterialTheme.colorScheme.primary,
                        unfocusedBorderColor = MaterialTheme.colorScheme.outline
                    )
                )

                Spacer(modifier = Modifier.height(10.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedButton(
                        onClick = {
                            DevBackendConfig.resetToDefault(context)
                            currentBaseUrl = DevBackendConfig.getBaseUrl(context)
                            customUrlInput = currentBaseUrl
                            urlUpdatedNotice = true
                        },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(6.dp)
                    ) {
                        Text("Reset Default", fontSize = 11.sp)
                    }

                    Button(
                        onClick = {
                            DevBackendConfig.setBaseUrl(context, customUrlInput)
                            currentBaseUrl = DevBackendConfig.getBaseUrl(context)
                            urlUpdatedNotice = true
                        },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(6.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.primary,
                            contentColor = MaterialTheme.colorScheme.onPrimary
                        )
                    ) {
                        Text("Save URL", fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    }
                }

                if (urlUpdatedNotice) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Updated: $currentBaseUrl",
                        style = MaterialTheme.typography.labelSmall,
                        color = AeroSemanticGreen,
                        fontSize = 11.sp
                    )
                }
            }

            // 4. Platform System Info
            AeroCard {
                Text(
                    text = "AEROVITAL PLATFORM INFO",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    letterSpacing = 0.5.sp
                )
                Spacer(modifier = Modifier.height(10.dp))

                ProfileFieldRow("App Version", "v1.2-monochrome-standalone")
                ProfileFieldRow("Package ID", "com.aerovital.phone")
                ProfileFieldRow("Target SDK", "Android API 35")
                ProfileFieldRow("Paired Hardware", "Samsung Galaxy Watch 4 (Wear OS)")
            }

            // 5. Logout CTA Button
            Button(
                onClick = onLogoutClick,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp),
                shape = RoundedCornerShape(8.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = AeroSemanticRed,
                    contentColor = Color.White
                )
            ) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.Logout,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "LOG OUT OF AEROVITAL SESSION",
                    fontWeight = FontWeight.Bold,
                    fontSize = 13.sp,
                    letterSpacing = 0.5.sp
                )
            }

            HardwareNonFabricationDisclaimer()
        }
    }
}

@Composable
private fun ThemeOptionButton(
    label: String,
    selected: Boolean,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val containerColor = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant
    val contentColor = if (selected) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant
    val borderColor = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(containerColor)
            .border(1.dp, borderColor, RoundedCornerShape(8.dp))
            .clickable(onClick = onClick)
            .padding(vertical = 12.dp, horizontal = 4.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(imageVector = icon, contentDescription = null, tint = contentColor, modifier = Modifier.size(18.dp))
            Spacer(modifier = Modifier.height(4.dp))
            Text(text = label, style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold, color = contentColor, fontSize = 11.sp)
        }
    }
}

@Composable
private fun ProfileFieldRow(label: String, value: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(text = label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 12.sp)
        Text(text = value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onSurface, fontSize = 12.sp)
    }
}
