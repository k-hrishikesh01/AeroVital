package com.aerovital.phone.ui.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.aerovital.phone.data.model.auth.AuthRequest
import com.aerovital.phone.data.remote.DevBackendConfig
import com.aerovital.phone.data.repository.AuthState
import com.aerovital.phone.ui.components.AeroCard
import com.aerovital.phone.ui.components.OfficialBrandEmblem
import com.aerovital.phone.ui.theme.*

@Composable
fun LoginScreen(
    viewModel: AuthViewModel,
    onLoginSuccess: () -> Unit
) {
    val state by viewModel.authState.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val scrollState = rememberScrollState()

    var username by remember { mutableStateOf("demo_researcher") }
    var password by remember { mutableStateOf("AeroVital2026!") }
    var currentUrl by remember { mutableStateOf(DevBackendConfig.getBaseUrl(context)) }

    LaunchedEffect(state) {
        if (state is AuthState.Authenticated) {
            onLoginSuccess()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .statusBarsPadding()
    ) {
        // Top Aviation Tricolour Stripe
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(3.dp)
        ) {
            Box(modifier = Modifier.weight(1f).fillMaxHeight().background(AeroTricolourSaffron))
            Box(modifier = Modifier.weight(1f).fillMaxHeight().background(AeroTricolourWhite))
            Box(modifier = Modifier.weight(1f).fillMaxHeight().background(AeroTricolourGreen))
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            // Official Aircraft Emblem & Title Lockup
            OfficialBrandEmblem(size = 72.dp)

            Spacer(modifier = Modifier.height(14.dp))
            Text(
                text = "AEROVITAL",
                style = MaterialTheme.typography.headlineLarge,
                fontWeight = FontWeight.ExtraBold,
                color = MaterialTheme.colorScheme.onSurface,
                letterSpacing = 2.sp
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Flight Deck Biometrics & Fatigue Intelligence",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 12.sp,
                letterSpacing = 0.5.sp
            )

            Spacer(modifier = Modifier.height(28.dp))

            // Login Container Card
            AeroCard {
                Text(
                    text = "PILOT AUTHENTICATION",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    letterSpacing = 0.5.sp
                )
                Spacer(modifier = Modifier.height(14.dp))

                OutlinedTextField(
                    value = username,
                    onValueChange = { username = it },
                    label = { Text("Callsign / Username", fontSize = 12.sp) },
                    leadingIcon = {
                        Icon(imageVector = Icons.Default.Person, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                    },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    shape = RoundedCornerShape(8.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = MaterialTheme.colorScheme.primary,
                        unfocusedBorderColor = MaterialTheme.colorScheme.outline
                    )
                )

                Spacer(modifier = Modifier.height(12.dp))

                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    label = { Text("Access Key / Password", fontSize = 12.sp) },
                    leadingIcon = {
                        Icon(imageVector = Icons.Default.Lock, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
                    },
                    visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    shape = RoundedCornerShape(8.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = MaterialTheme.colorScheme.primary,
                        unfocusedBorderColor = MaterialTheme.colorScheme.outline
                    )
                )

                Spacer(modifier = Modifier.height(20.dp))

                Button(
                    onClick = { viewModel.login(AuthRequest(username.trim(), password)) },
                    enabled = state !is AuthState.Authenticating && username.isNotBlank() && password.isNotBlank(),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp),
                    shape = RoundedCornerShape(8.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary,
                        contentColor = MaterialTheme.colorScheme.onPrimary
                    )
                ) {
                    if (state is AuthState.Authenticating) {
                        CircularProgressIndicator(modifier = Modifier.size(20.dp), color = MaterialTheme.colorScheme.onPrimary, strokeWidth = 2.dp)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Verifying Credentials...", fontSize = 13.sp, fontWeight = FontWeight.Bold)
                    } else {
                        Text("SIGN IN TO FLIGHT SESSION", fontSize = 13.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.5.sp)
                    }
                }

                if (state is AuthState.Error) {
                    Spacer(modifier = Modifier.height(12.dp))
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(6.dp))
                            .background(AeroSemanticRed.copy(alpha = 0.12f))
                            .border(1.dp, AeroSemanticRed.copy(alpha = 0.4f), RoundedCornerShape(6.dp))
                            .padding(10.dp)
                    ) {
                        Text(
                            text = (state as AuthState.Error).message,
                            style = MaterialTheme.typography.bodySmall,
                            color = AeroSemanticRed,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(20.dp))

            // Centrally Configured Production Endpoint Card
            AeroCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "DJANGO REST API BASE URL",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 10.sp
                    )
                    Text(
                        text = if (currentUrl.contains("onrender.com")) "PRODUCTION" else "LOCAL DEV",
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold,
                        color = if (currentUrl.contains("onrender.com")) AeroSemanticGreen else AeroSemanticAmber,
                        fontSize = 9.sp
                    )
                }
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = currentUrl,
                    fontFamily = FontFamily.Monospace,
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurface,
                    fontWeight = FontWeight.SemiBold
                )
                Spacer(modifier = Modifier.height(10.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    OutlinedButton(
                        onClick = {
                            DevBackendConfig.setBaseUrl(context, DevBackendConfig.PRODUCTION_API_URL)
                            currentUrl = DevBackendConfig.getBaseUrl(context)
                        },
                        modifier = Modifier.weight(1.2f),
                        shape = RoundedCornerShape(6.dp),
                        contentPadding = PaddingValues(vertical = 4.dp, horizontal = 4.dp),
                        colors = ButtonDefaults.outlinedButtonColors(
                            containerColor = if (currentUrl == DevBackendConfig.PRODUCTION_API_URL) MaterialTheme.colorScheme.surfaceVariant else Color.Transparent
                        )
                    ) {
                        Text("Production", fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    }
                    OutlinedButton(
                        onClick = {
                            DevBackendConfig.setBaseUrl(context, DevBackendConfig.DEFAULT_ADB_REVERSE_URL)
                            currentUrl = DevBackendConfig.getBaseUrl(context)
                        },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(6.dp),
                        contentPadding = PaddingValues(vertical = 4.dp, horizontal = 4.dp),
                        colors = ButtonDefaults.outlinedButtonColors(
                            containerColor = if (currentUrl == DevBackendConfig.DEFAULT_ADB_REVERSE_URL) MaterialTheme.colorScheme.surfaceVariant else Color.Transparent
                        )
                    ) {
                        Text("127.0.0.1 (ADB)", fontSize = 10.sp)
                    }
                    OutlinedButton(
                        onClick = {
                            DevBackendConfig.setBaseUrl(context, DevBackendConfig.DEFAULT_EMULATOR_URL)
                            currentUrl = DevBackendConfig.getBaseUrl(context)
                        },
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(6.dp),
                        contentPadding = PaddingValues(vertical = 4.dp, horizontal = 4.dp),
                        colors = ButtonDefaults.outlinedButtonColors(
                            containerColor = if (currentUrl == DevBackendConfig.DEFAULT_EMULATOR_URL) MaterialTheme.colorScheme.surfaceVariant else Color.Transparent
                        )
                    ) {
                        Text("10.0.2.2 (Emu)", fontSize = 10.sp)
                    }
                }
            }
        }
    }
}
