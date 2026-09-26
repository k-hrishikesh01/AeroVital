package com.example.aerovital.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp

@Composable
fun LoginScreen(
    onLogin: (String, String) -> Unit,
    onForgotPassword: () -> Unit,
    onCreateAccount: () -> Unit,
    isLoading: Boolean = false,
    errorMessage: String? = null
) {
    var pilotId by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .imePadding()
            .padding(horizontal = 28.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {

        Spacer(modifier = Modifier.height(60.dp))

        Text(
            text = "Aero Vital",
            style = MaterialTheme.typography.headlineLarge
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "Pilot Health & Performance Monitoring",
            style = MaterialTheme.typography.bodyMedium
        )

        Spacer(modifier = Modifier.height(50.dp))

        Text(
            text = "Pilot Login",
            style = MaterialTheme.typography.headlineMedium
        )

        Spacer(modifier = Modifier.height(28.dp))

        if (!errorMessage.isNullOrBlank()) {
            Text(
                text = errorMessage,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(bottom = 12.dp)
            )
        }

        /*
         * PILOT ID
         */
        OutlinedTextField(
            value = pilotId,
            onValueChange = { pilotId = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("Pilot ID") },
            placeholder = { Text("Enter Pilot ID (e.g. AVP-2026-001)") },
            shape = RoundedCornerShape(12.dp),
            enabled = !isLoading
        )

        Spacer(modifier = Modifier.height(16.dp))

        /*
         * PASSWORD
         */
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("Password") },
            placeholder = { Text("Enter Password") },
            leadingIcon = {
                Icon(
                    imageVector = Icons.Default.Lock,
                    contentDescription = "Password"
                )
            },
            visualTransformation = PasswordVisualTransformation(),
            shape = RoundedCornerShape(12.dp),
            enabled = !isLoading
        )

        Spacer(modifier = Modifier.height(8.dp))

        /*
         * FORGOT PASSWORD
         */
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.End
        ) {
            TextButton(
                onClick = onForgotPassword,
                enabled = !isLoading
            ) {
                Text(text = "Forgot Password?")
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        /*
         * LOGIN BUTTON
         */
        Button(
            onClick = { onLogin(pilotId, password) },
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp),
            shape = RoundedCornerShape(12.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.primary
            ),
            enabled = !isLoading
        ) {
            if (isLoading) {
                CircularProgressIndicator(
                    color = MaterialTheme.colorScheme.onPrimary,
                    modifier = Modifier.size(24.dp)
                )
            } else {
                Text(text = "LOGIN")
            }
        }

        Spacer(modifier = Modifier.height(20.dp))

        /*
         * CREATE ACCOUNT
         */
        Row(
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(text = "Don't have an account?")
            TextButton(
                onClick = onCreateAccount,
                enabled = !isLoading
            ) {
                Text(text = "Create Account")
            }
        }
    }
}
