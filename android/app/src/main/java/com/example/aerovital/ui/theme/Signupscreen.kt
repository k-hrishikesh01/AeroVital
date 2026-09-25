package com.example.aerovital.ui

import androidx.compose.foundation.layout.Arrangement
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
fun SignUpScreen(
    onBack: () -> Unit,
    onCreateAccount: (String, String, String) -> Unit
) {

    var pilotId by rememberSaveable {
        mutableStateOf("")
    }

    var name by rememberSaveable {
        mutableStateOf("")
    }

    var password by rememberSaveable {
        mutableStateOf("")
    }


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


        Spacer(
            modifier = Modifier.height(24.dp)
        )


        OutlinedTextField(
            value = name,
            onValueChange = {
                name = it
            },

            modifier = Modifier.fillMaxWidth(),

            singleLine = true,

            label = {
                Text("Pilot Name")
            },

            shape = RoundedCornerShape(12.dp)
        )


        Spacer(
            modifier = Modifier.height(14.dp)
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
            modifier = Modifier.height(14.dp)
        )


        OutlinedTextField(
            value = password,
            onValueChange = {
                password = it
            },

            modifier = Modifier.fillMaxWidth(),

            singleLine = true,

            label = {
                Text("Password")
            },

            shape = RoundedCornerShape(12.dp)
        )


        Spacer(
            modifier = Modifier.height(24.dp)
        )


        Button(
            onClick = {
                onCreateAccount(
                    name,
                    pilotId,
                    password
                )
            },

            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp),

            shape = RoundedCornerShape(12.dp)
        ) {

            Text(
                text = "CREATE ACCOUNT"
            )
        }


        Spacer(
            modifier = Modifier.height(10.dp)
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