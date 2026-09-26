package com.aerovital.phone.data.remote

/**
 * Functional interface to supply an authenticated token without coupling to token storage or UI state.
 */
fun interface TokenProvider {
    fun getToken(): String?
}
