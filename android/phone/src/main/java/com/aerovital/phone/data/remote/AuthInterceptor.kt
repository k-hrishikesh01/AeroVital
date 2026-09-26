package com.aerovital.phone.data.remote

import okhttp3.Interceptor
import okhttp3.Response

class AuthInterceptor(private val tokenManager: TokenManager) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val requestBuilder = chain.request().newBuilder()

        // If we have a token, add the Authorization header
        tokenManager.getToken()?.let { token ->
            requestBuilder.addHeader("Authorization", "Token $token")
        }

        return chain.proceed(requestBuilder.build())
    }
}
