package com.aerovital.phone.data.remote

import com.aerovital.phone.data.model.auth.AuthRequest
import com.aerovital.phone.data.model.auth.AuthResponse
import com.aerovital.phone.data.model.auth.MeResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface AuthApi {
    @POST("api/v1/auth/token/")
    suspend fun login(@Body request: AuthRequest): Response<AuthResponse>

    @GET("api/v1/auth/me/")
    suspend fun getMe(): Response<MeResponse>

    @POST("api/v1/auth/logout/")
    suspend fun logout(): Response<Unit>
}
