package com.aerovital.phone.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.NavigationDrawerItemDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.aerovital.phone.data.model.auth.PilotProfile
import com.aerovital.phone.ui.navigation.AppScreen
import com.aerovital.phone.ui.theme.AeroDarkDrawerHeader
import com.aerovital.phone.ui.theme.AeroDarkGreen
import com.aerovital.phone.ui.theme.AeroGreen
import com.aerovital.phone.ui.theme.LocalThemeIsDark
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.Locale

@Composable
fun DashboardScreen(
    username: String? = null,
    pilot: PilotProfile?,
    latestHeartRate: Double? = null,
    onNavigate: (AppScreen) -> Unit,
    onLogoutClick: () -> Unit
) {
    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    val scrollState = rememberScrollState()

    // Session timer starting from screen initialization
    var sessionSeconds by remember { mutableLongStateOf(0L) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(1000L)
            sessionSeconds++
        }
    }

    val hours = sessionSeconds / 3600
    val minutes = (sessionSeconds % 3600) / 60
    val seconds = sessionSeconds % 60
    val formattedTime = String.format(Locale.US, "%02d:%02d:%02d", hours, minutes, seconds)

    val displayName = pilot?.name?.takeIf { it.isNotBlank() } ?: username ?: "Pilot"
    val pilotCode = pilot?.pilotCode?.takeIf { it.isNotBlank() } ?: "--"
    val isPilotActive = pilot?.isActive == true

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet(
                modifier = Modifier.width(310.dp)
            ) {
                val isDark = LocalThemeIsDark.current
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(if (isDark) AeroDarkDrawerHeader else MaterialTheme.colorScheme.primary)
                        .padding(24.dp)
                ) {
                    Text(
                        text = "AEROVITAL",
                        style = MaterialTheme.typography.headlineMedium,
                        fontWeight = FontWeight.Bold,
                        color = if (isDark) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onPrimary
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Flight Biometrics & Fatigue Intelligence",
                        style = MaterialTheme.typography.bodySmall,
                        color = if (isDark) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.8f)
                    )
                    Spacer(modifier = Modifier.height(14.dp))
                    Text(
                        text = displayName,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = if (isDark) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onPrimary
                    )
                    Text(
                        text = "Pilot Code: $pilotCode",
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (isDark) MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.85f)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .background(
                                    if (isPilotActive) (if (isDark) AeroDarkGreen else AeroGreen) else Color.Gray,
                                    shape = CircleShape
                                )
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = if (isPilotActive) "ACTIVE • AUTHORIZED" else "INACTIVE",
                            style = MaterialTheme.typography.labelSmall,
                            color = if (isDark) (if (isPilotActive) AeroDarkGreen else MaterialTheme.colorScheme.onSurfaceVariant) else MaterialTheme.colorScheme.onPrimary
                        )
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                DrawerItem(
                    icon = Icons.Default.Dashboard,
                    label = "Dashboard",
                    onClick = { scope.launch { drawerState.close() } }
                )

                DrawerItem(
                    icon = Icons.Default.Info,
                    label = "Details",
                    onClick = {
                        scope.launch { drawerState.close() }
                        onNavigate(AppScreen.DETAILS)
                    }
                )

                DrawerItem(
                    icon = Icons.Default.History,
                    label = "History",
                    onClick = {
                        scope.launch { drawerState.close() }
                        onNavigate(AppScreen.HISTORY)
                    }
                )

                DrawerItem(
                    icon = Icons.Default.Person,
                    label = "Profile",
                    onClick = {
                        scope.launch { drawerState.close() }
                        onNavigate(AppScreen.PROFILE)
                    }
                )

                DrawerItem(
                    icon = Icons.Default.Settings,
                    label = "Settings",
                    onClick = {
                        scope.launch { drawerState.close() }
                        onNavigate(AppScreen.SETTINGS)
                    }
                )

                HorizontalDivider(modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp))

                DrawerItem(
                    icon = Icons.Default.Build,
                    label = "Developer / Hardware Diagnostics",
                    onClick = {
                        scope.launch { drawerState.close() }
                        onNavigate(AppScreen.DIAGNOSTICS)
                    }
                )

                HorizontalDivider(modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp))

                DrawerItem(
                    icon = Icons.Default.Lock,
                    label = "Logout",
                    onClick = {
                        scope.launch { drawerState.close() }
                        onLogoutClick()
                    }
                )
            }
        }
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.background)
                .statusBarsPadding()
        ) {
            /*
             * TOP APP BAR
             */
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                IconButton(
                    onClick = {
                        scope.launch {
                            if (drawerState.isClosed) drawerState.open() else drawerState.close()
                        }
                    }
                ) {
                    Icon(
                        imageVector = Icons.Default.Menu,
                        contentDescription = "Menu",
                        tint = MaterialTheme.colorScheme.primary
                    )
                }

                Text(
                    text = "AEROVITAL",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary,
                    letterSpacing = 1.5.sp
                )

                IconButton(
                    onClick = { onNavigate(AppScreen.PROFILE) }
                ) {
                    Icon(
                        imageVector = Icons.Default.AccountCircle,
                        contentDescription = "Profile",
                        tint = MaterialTheme.colorScheme.primary
                    )
                }
            }

            /*
             * MAIN CONTENT
             */
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(scrollState)
                    .padding(horizontal = 20.dp, vertical = 8.dp)
            ) {
                Text(
                    text = "Welcome, $displayName",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onBackground
                )
                Text(
                    text = "Pilot Code: $pilotCode • ${if (isPilotActive) "Active Flight Status" else "Inactive"}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.secondary
                )

                Spacer(modifier = Modifier.height(18.dp))

                Text(
                    text = "Current Session",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )

                Spacer(modifier = Modifier.height(8.dp))

                /*
                 * SESSION TIME CARD
                 */
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surface
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "Active Session Elapsed",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Box(
                                modifier = Modifier
                                    .background(
                                        MaterialTheme.colorScheme.primaryContainer,
                                        shape = RoundedCornerShape(8.dp)
                                    )
                                    .padding(horizontal = 8.dp, vertical = 4.dp)
                            ) {
                                Text(
                                    text = if (isPilotActive) "READY" else "STANDBY",
                                    style = MaterialTheme.typography.labelSmall,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onPrimaryContainer
                                )
                            }
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = formattedTime,
                            style = MaterialTheme.typography.headlineLarge,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "Authenticated with Django backend via Keystore",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                /*
                 * SCORE CARDS (S-Score and Confidence)
                 */
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    ScoreCard(
                        title = "S-Score",
                        value = "-- %",
                        subtitle = "Watch Standby",
                        modifier = Modifier
                            .weight(1f)
                            .clickable { onNavigate(AppScreen.DETAILS) }
                    )

                    ScoreCard(
                        title = "Confidence",
                        value = "-- %",
                        subtitle = "Awaiting Stream",
                        modifier = Modifier
                            .weight(1f)
                            .clickable { onNavigate(AppScreen.DETAILS) }
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                /*
                 * CONDITION CARD
                 */
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onNavigate(AppScreen.DETAILS) },
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surface
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "Current Condition",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(
                                text = "Details →",
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = if (latestHeartRate != null) "PHYSIOLOGICAL MONITORING" else "WATCH STANDBY",
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.secondary
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = if (latestHeartRate != null) {
                                "Galaxy Watch biometrics active • Heart rate streaming live to flight deck"
                            } else {
                                "Galaxy Watch is updating / charging • Telemetry stream will resume when online"
                            },
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                Spacer(modifier = Modifier.height(20.dp))

                /*
                 * DETAILS SECTION
                 */
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Telemetry & Hardware",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        text = "View All",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.clickable { onNavigate(AppScreen.DETAILS) }
                    )
                }

                Spacer(modifier = Modifier.height(8.dp))

                DetailRow(
                    icon = {
                        Icon(
                            imageVector = Icons.Default.Favorite,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary
                        )
                    },
                    title = "Heart Rate Monitor",
                    value = if (latestHeartRate != null) "${kotlin.math.round(latestHeartRate).toInt()} BPM" else "-- BPM (Standby)",
                    onClick = { onNavigate(AppScreen.DETAILS) }
                )

                DetailRow(
                    icon = {
                        Icon(
                            imageVector = Icons.Default.Speed,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.secondary
                        )
                    },
                    title = "Fatigue Assessment",
                    value = "Nominal",
                    onClick = { onNavigate(AppScreen.DETAILS) }
                )

                DetailRow(
                    icon = {
                        Icon(
                            imageVector = Icons.Default.Build,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary
                        )
                    },
                    title = "Developer / Hardware Diagnostics",
                    value = "A7 Ready →",
                    onClick = { onNavigate(AppScreen.DIAGNOSTICS) }
                )

                DetailRow(
                    icon = {
                        Icon(
                            imageVector = Icons.Default.History,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.secondary
                        )
                    },
                    title = "Flight Session History",
                    value = "View History",
                    onClick = { onNavigate(AppScreen.HISTORY) }
                )

                Spacer(modifier = Modifier.height(24.dp))
            }
        }
    }
}

@Composable
private fun DrawerItem(
    icon: ImageVector,
    label: String,
    onClick: () -> Unit
) {
    NavigationDrawerItem(
        icon = { Icon(imageVector = icon, contentDescription = label) },
        label = { Text(text = label, fontWeight = FontWeight.Medium) },
        selected = false,
        onClick = onClick,
        modifier = Modifier.padding(NavigationDrawerItemDefaults.ItemPadding)
    )
}

@Composable
private fun ScoreCard(
    title: String,
    value: String,
    subtitle: String,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = value,
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun DetailRow(
    icon: @Composable () -> Unit,
    title: String,
    value: String,
    onClick: () -> Unit = {}
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() }
            .padding(vertical = 4.dp),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            icon()
            Spacer(modifier = Modifier.width(14.dp))
            Text(
                text = title,
                modifier = Modifier.weight(1f),
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Medium
            )
            Text(
                text = value,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}
