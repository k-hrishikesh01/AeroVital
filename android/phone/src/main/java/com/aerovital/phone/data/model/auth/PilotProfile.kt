package com.aerovital.phone.data.model.auth

import com.google.gson.annotations.SerializedName

data class PilotProfile(
    @SerializedName("id") val id: String,
    @SerializedName("pilot_code") val pilotCode: String,
    @SerializedName("name") val name: String,
    @SerializedName("age") val age: Int?,
    @SerializedName("sex") val sex: String?,
    @SerializedName("is_active") val isActive: Boolean,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("updated_at") val updatedAt: String
)
