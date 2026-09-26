package com.aerovital.phone.data.remote

interface TokenManager {
    fun saveToken(token: String)
    fun getToken(): String?
    fun clearToken()
}
