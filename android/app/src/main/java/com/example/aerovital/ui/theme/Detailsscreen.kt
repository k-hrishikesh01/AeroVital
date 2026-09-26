package com.example.aerovital.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.aerovital.data.model.PilotProfile

@Composable
fun DetailsScreen(
    profile: PilotProfile,
    onBack: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .padding(20.dp)
    ) {

        /*
         * TOP BAR
         */
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onBack) {
                Icon(imageVector = Icons.Default.ArrowBack, contentDescription = "Back")
            }
            Text(
                text = "Telemetry & Session Details",
                style = MaterialTheme.typography.titleLarge,
                modifier = Modifier.padding(start = 12.dp)
            )
        }

        Spacer(modifier = Modifier.height(20.dp))

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
        ) {
            Column(modifier = Modifier.padding(20.dp)) {
                Text(text = "Pilot Identification", style = MaterialTheme.typography.titleMedium)
                Spacer(modifier = Modifier.height(8.dp))
                Text(text = "Name: ${profile.fullName}", style = MaterialTheme.typography.bodyLarge)
                Text(text = "Pilot ID: ${profile.pilotId}", style = MaterialTheme.typography.bodyMedium)
                Text(text = "Status: ${profile.status}", style = MaterialTheme.typography.bodyMedium)
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        Text(text = "Live Telemetry Metrics", style = MaterialTheme.typography.titleMedium)
        Spacer(modifier = Modifier.height(10.dp))

        MetricDetailCard(
            icon = { Icon(imageVector = Icons.Default.FavoriteBorder, contentDescription = null) },
            title = "Heart Rate Monitor",
            value = "78 BPM",
            description = "Normal resting heart rate range"
        )

        Spacer(modifier = Modifier.height(10.dp))

        MetricDetailCard(
            icon = { Icon(imageVector = Icons.Default.Speed, contentDescription = null) },
            title = "S-Score (Sleepiness Index)",
            value = "78%",
            description = "Optimal alertness threshold maintained"
        )

        Spacer(modifier = Modifier.height(10.dp))

        MetricDetailCard(
            icon = { Icon(imageVector = Icons.Default.Info, contentDescription = null) },
            title = "Fatigue State Assessment",
            value = "LOW FATIGUE",
            description = "Safe operational state for flight duty"
        )
    }
}

@Composable
private fun MetricDetailCard(
    icon: @Composable () -> Unit,
    title: String,
    value: String,
    description: String
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            icon()
            Spacer(modifier = Modifier.padding(horizontal = 10.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(text = title, style = MaterialTheme.typography.bodyLarge)
                Text(text = description, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Text(text = value, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
        }
    }
}
