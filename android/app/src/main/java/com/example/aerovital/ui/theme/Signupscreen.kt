package com.example.aerovital.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp

@Composable
fun SignUpScreen(
    onBack: () -> Unit,
    onCreateAccount: (String, String, String, String) -> Unit,
    isLoading: Boolean = false,
    errorMessage: String? = null
) {
    var name by rememberSaveable { mutableStateOf("") }
    var pilotId by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var confirmPassword by rememberSaveable { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center
    ) {

        Text(
            text = "Create Pilot Account",
            style = MaterialTheme.typography.headlineMedium
        )

        Spacer(modifier = Modifier.height(24.dp))

        if (!errorMessage.isNullOrBlank()) {
            Text(
                text = errorMessage,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(bottom = 12.dp)
            )
        }

        OutlinedTextField(
            value = name,
            onValueChange = { name = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("Full Name") },
            placeholder = { Text("e.g. Ananya V") },
            shape = RoundedCornerShape(12.dp),
            enabled = !isLoading
        )

        Spacer(modifier = Modifier.height(14.dp))

        OutlinedTextField(
            value = pilotId,
            onValueChange = { pilotId = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("Pilot ID") },
            placeholder = { Text("e.g. AVP-2026-001") },
            shape = RoundedCornerShape(12.dp),
            enabled = !isLoading
        )

        Spacer(modifier = Modifier.height(14.dp))

        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("Password") },
            placeholder = { Text("At least 8 chars, 1 upper, 1 lower, 1 num, 1 special") },
            visualTransformation = PasswordVisualTransformation(),
            shape = RoundedCornerShape(12.dp),
            enabled = !isLoading
        )

        Spacer(modifier = Modifier.height(14.dp))

        OutlinedTextField(
            value = confirmPassword,
            onValueChange = { confirmPassword = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            label = { Text("Confirm Password") },
            placeholder = { Text("Re-enter Password") },
            visualTransformation = PasswordVisualTransformation(),
            shape = RoundedCornerShape(12.dp),
            enabled = !isLoading
        )

        Spacer(modifier = Modifier.height(24.dp))

        Button(
            onClick = {
                onCreateAccount(name, pilotId, password, confirmPassword)
            },
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp),
            shape = RoundedCornerShape(12.dp),
            enabled = !isLoading
        ) {
            if (isLoading) {
                CircularProgressIndicator(
                    color = MaterialTheme.colorScheme.onPrimary,
                    modifier = Modifier.size(24.dp)
                )
            } else {
                Text(text = "CREATE ACCOUNT")
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        TextButton(
            onClick = onBack,
            enabled = !isLoading
        ) {
            Text(text = "Back to Login")
        }
    }
}
