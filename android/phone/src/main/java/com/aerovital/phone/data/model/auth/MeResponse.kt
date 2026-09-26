package com.aerovital.phone.data.model.auth

import com.google.gson.annotations.SerializedName

data class MeResponse(
    @SerializedName("user_id") val userId: Int,
    @SerializedName("username") val username: String,
    @SerializedName("email") val email: String?,
    @SerializedName("pilot") val pilot: PilotProfile?
)
