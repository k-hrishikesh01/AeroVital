package com.example.aerovital.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
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
import androidx.compose.ui.unit.dp


@Composable
fun ForgotPasswordScreen(
    onBack: () -> Unit,
    onResetPassword: (String) -> Unit
) {

    var pilotId by rememberSaveable {
        mutableStateOf("")
    }


    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp)
    ) {

        Spacer(
            modifier = Modifier.height(60.dp)
        )


        Text(
            text = "Reset Password",
            style = MaterialTheme.typography.headlineMedium
        )


        Spacer(
            modifier = Modifier.height(12.dp)
        )


        Text(
            text = "Enter your Pilot ID to begin the password recovery process.",
            style = MaterialTheme.typography.bodyMedium
        )


        Spacer(
            modifier = Modifier.height(30.dp)
        )


        OutlinedTextField(
            value = pilotId,

            onValueChange = {
                pilotId = it
            },

            modifier = Modifier.fillMaxWidth(),

            singleLine = true,

            label = {
                Text("Pilot ID")
            },

            shape = RoundedCornerShape(12.dp)
        )


        Spacer(
            modifier = Modifier.height(20.dp)
        )


        Button(
            onClick = {
                onResetPassword(pilotId)
            },

            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp),

            shape = RoundedCornerShape(12.dp)
        ) {

            Text(
                text = "RESET PASSWORD"
            )
        }


        Spacer(
            modifier = Modifier.height(12.dp)
        )


        TextButton(
            onClick = onBack
        ) {

            Text(
                text = "Back to Login"
            )
        }
    }
}