package com.aerovital.phone.ui.auth

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.aerovital.phone.data.model.auth.AuthRequest
import com.aerovital.phone.data.repository.AuthState

@Composable
fun LoginScreen(
    viewModel: AuthViewModel,
    onLoginSuccess: () -> Unit
) {
    val state by viewModel.authState.collectAsStateWithLifecycle()

    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }

    LaunchedEffect(state) {
        if (state is AuthState.Authenticated) {
            onLoginSuccess()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(
            text = "AEROVITAL",
            style = MaterialTheme.typography.headlineLarge,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary,
            letterSpacing = 2.sp
        )
        Spacer(modifier = Modifier.height(6.dp))
        Text(
            text = "Flight Biometrics & Fatigue Intelligence",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.secondary
        )
        Spacer(modifier = Modifier.height(28.dp))
        Text(
            text = "Pilot Authentication",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold
        )

        OutlinedTextField(
            value = username,
            onValueChange = { username = it },
            label = { Text("Username") },
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(16.dp))

        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("Password") },
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(24.dp))

        Button(
            onClick = { viewModel.login(AuthRequest(username, password)) },
            enabled = state !is AuthState.Authenticating && username.isNotBlank() && password.isNotBlank(),
            modifier = Modifier.fillMaxWidth()
        ) {
            if (state is AuthState.Authenticating) {
                CircularProgressIndicator(modifier = Modifier.size(24.dp), color = MaterialTheme.colorScheme.onPrimary)
            } else {
                Text("Login")
            }
        }

        if (state is AuthState.Error) {
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = (state as AuthState.Error).message,
                color = MaterialTheme.colorScheme.error
            )
        }

        Spacer(modifier = Modifier.height(32.dp))

        // Development Server URL configuration
        val context = androidx.compose.ui.platform.LocalContext.current
        var currentUrl by remember { mutableStateOf(com.aerovital.phone.data.remote.DevBackendConfig.getBaseUrl(context)) }

        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
        ) {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(text = "Dev Server: $currentUrl", style = MaterialTheme.typography.bodySmall)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    TextButton(onClick = {
                        com.aerovital.phone.data.remote.DevBackendConfig.setBaseUrl(
                            context,
                            com.aerovital.phone.data.remote.DevBackendConfig.DEFAULT_ADB_REVERSE_URL
                        )
                        currentUrl = com.aerovital.phone.data.remote.DevBackendConfig.getBaseUrl(context)
                    }) {
                        Text("127.0.0.1 (ADB)")
                    }
                    TextButton(onClick = {
                        com.aerovital.phone.data.remote.DevBackendConfig.setBaseUrl(
                            context,
                            com.aerovital.phone.data.remote.DevBackendConfig.DEFAULT_EMULATOR_URL
                        )
                        currentUrl = com.aerovital.phone.data.remote.DevBackendConfig.getBaseUrl(context)
                    }) {
                        Text("10.0.2.2 (Emu)")
                    }
                }
            }
        }
    }
}
