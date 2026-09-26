package com.example.aerovital.data.model

data class PilotProfile(
    val pilotId: String = "",
    val fullName: String = "",
    val recoveryEmail: String = "",
    val authUid: String = "",
    val createdAt: Long = System.currentTimeMillis(),
    val status: String = "ACTIVE"
)
