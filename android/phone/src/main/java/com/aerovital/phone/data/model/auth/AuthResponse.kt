package com.aerovital.phone.data.model.auth

import com.google.gson.annotations.SerializedName

data class AuthResponse(
    @SerializedName("token") val token: String,
    @SerializedName("user_id") val userId: Int,
    @SerializedName("username") val username: String,
    @SerializedName("pilot") val pilot: PilotProfile?
)
