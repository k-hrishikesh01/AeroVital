package com.example.aerovital.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.FavoriteBorder
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
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import com.example.aerovital.data.model.PilotProfile
import kotlinx.coroutines.launch

@Composable
fun DashboardScreen(
    profile: PilotProfile,
    onMenuClick: () -> Unit = {},
    onProfileClick: () -> Unit = {},
    onDetailsClick: () -> Unit = {},
    onHistoryClick: () -> Unit = {},
    onSettingsClick: () -> Unit = {},
    onLogoutClick: () -> Unit = {}
) {
    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    val scope = rememberCoroutineScope()

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet(
                modifier = Modifier.width(300.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(MaterialTheme.colorScheme.primary)
                        .padding(24.dp)
                ) {
                    Text(
                        text = "Aero Vital",
                        style = MaterialTheme.typography.headlineMedium,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = profile.fullName.ifBlank { "Pilot Name" },
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                    Text(
                        text = "Pilot ID: ${profile.pilotId}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.8f)
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                DrawerItem(
                    icon = Icons.Default.Menu,
                    label = "Dashboard",
                    onClick = {
                        scope.launch { drawerState.close() }
                    }
                )

                DrawerItem(
                    icon = Icons.Default.Info,
                    label = "Details",
                    onClick = {
                        scope.launch { drawerState.close() }
                        onDetailsClick()
                    }
                )

                DrawerItem(
                    icon = Icons.Default.History,
                    label = "History",
                    onClick = {
                        scope.launch { drawerState.close() }
                        onHistoryClick()
                    }
                )

                DrawerItem(
                    icon = Icons.Default.Person,
                    label = "Profile",
                    onClick = {
                        scope.launch { drawerState.close() }
                        onProfileClick()
                    }
                )

                DrawerItem(
                    icon = Icons.Default.Settings,
                    label = "Settings",
                    onClick = {
                        scope.launch { drawerState.close() }
                        onSettingsClick()
                    }
                )

                HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp))

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
                        onMenuClick()
                    }
                ) {
                    Icon(
                        imageVector = Icons.Default.Menu,
                        contentDescription = "Menu"
                    )
                }

                Text(
                    text = "AEROVITAL",
                    style = MaterialTheme.typography.titleLarge
                )

                IconButton(
                    onClick = onProfileClick
                ) {
                    Icon(
                        imageVector = Icons.Default.AccountCircle,
                        contentDescription = "Profile"
                    )
                }
            }

            /*
             * MAIN CONTENT
             */
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp)
            ) {

                Spacer(modifier = Modifier.height(10.dp))

                Text(
                    text = "Welcome, ${profile.fullName.ifBlank { "Pilot" }} (${profile.pilotId})",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.primary
                )

                Spacer(modifier = Modifier.height(16.dp))

                Text(
                    text = "Current Session",
                    style = MaterialTheme.typography.titleMedium
                )

                Spacer(modifier = Modifier.height(12.dp))

                /*
                 * SESSION TIME
                 */
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surface
                    )
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp)
                    ) {
                        Text(
                            text = "Session Time",
                            style = MaterialTheme.typography.bodyMedium
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = "02:45:32",
                            style = MaterialTheme.typography.headlineMedium
                        )
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                /*
                 * SCORE CARDS
                 */
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    ScoreCard(
                        title = "S-Score",
                        value = "78%",
                        modifier = Modifier
                            .weight(1f)
                            .clickable { onDetailsClick() }
                    )

                    ScoreCard(
                        title = "Conference",
                        value = "50%",
                        modifier = Modifier
                            .weight(1f)
                            .clickable { onDetailsClick() }
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                /*
                 * CONDITION
                 */
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onDetailsClick() },
                    shape = RoundedCornerShape(16.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp)
                    ) {
                        Text(
                            text = "Current Condition",
                            style = MaterialTheme.typography.bodyMedium
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "NORMAL",
                            style = MaterialTheme.typography.headlineSmall
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "Last estimated 2 minutes ago",
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                }

                Spacer(modifier = Modifier.height(20.dp))

                /*
                 * DETAILS
                 */
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Details",
                        style = MaterialTheme.typography.titleMedium
                    )
                    Text(
                        text = "View All",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.clickable { onDetailsClick() }
                    )
                }

                Spacer(modifier = Modifier.height(10.dp))

                DetailRow(
                    icon = { Icon(imageVector = Icons.Default.FavoriteBorder, contentDescription = null) },
                    title = "Heart Rate",
                    value = "78 BPM",
                    onClick = onDetailsClick
                )

                DetailRow(
                    icon = { Icon(imageVector = Icons.Default.Info, contentDescription = null) },
                    title = "Fatigue State",
                    value = "Low",
                    onClick = onDetailsClick
                )

                DetailRow(
                    icon = { Icon(imageVector = Icons.Default.History, contentDescription = null) },
                    title = "Last Session",
                    value = "Today",
                    onClick = onHistoryClick
                )
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
        label = { Text(text = label) },
        selected = false,
        onClick = onClick,
        modifier = Modifier.padding(NavigationDrawerItemDefaults.ItemPadding)
    )
}

@Composable
private fun ScoreCard(
    title: String,
    value: String,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.bodyMedium
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = value,
                style = MaterialTheme.typography.headlineSmall
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
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() }
            .padding(vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        icon()
        Spacer(modifier = Modifier.padding(horizontal = 12.dp))
        Text(
            text = title,
            modifier = Modifier.weight(1f),
            style = MaterialTheme.typography.bodyLarge
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium
        )
    }
}
