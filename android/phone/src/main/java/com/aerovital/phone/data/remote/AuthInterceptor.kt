package com.aerovital.phone.data.remote

import okhttp3.Interceptor
import okhttp3.Response

class AuthInterceptor(private val tokenManager: TokenManager) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val path = request.url.encodedPath

        // Never attach Authorization header to authentication endpoints (login, token)
        if (path.endsWith("auth/token/") || path.contains("auth/token")) {
            return chain.proceed(request)
        }

        val requestBuilder = request.newBuilder()

        // If we have a token, add the Authorization header
        tokenManager.getToken()?.let { token ->
            requestBuilder.addHeader("Authorization", "Token $token")
        }

        return chain.proceed(requestBuilder.build())
    }
}
