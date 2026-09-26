package com.aerovital.phone.data.remote

interface TokenManager : TokenProvider {
    fun saveToken(token: String)
    override fun getToken(): String?
    fun clearToken()
}
