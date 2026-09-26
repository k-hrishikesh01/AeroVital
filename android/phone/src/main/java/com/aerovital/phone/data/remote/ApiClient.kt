package com.aerovital.phone.data.remote

import android.content.Context
import com.aerovital.phone.BuildConfig
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {
    private var retrofit: Retrofit? = null

    // This can be changed in UI or dev settings, but defaults to a common local IP for emulator
    var BASE_URL = "http://10.0.2.2:8000/"
        set(value) {
            field = value
            retrofit = null // Force recreation on next get
        }

    fun getRetrofit(context: Context, onUnauthorized: () -> Unit): Retrofit {
        if (retrofit == null) {
            val tokenManager = SecureTokenManager(context)

            val loggingInterceptor = HttpLoggingInterceptor().apply {
                level = if (BuildConfig.DEBUG) {
                    // Use HEADERS instead of BODY to avoid logging passwords in request bodies
                    HttpLoggingInterceptor.Level.HEADERS
                } else {
                    HttpLoggingInterceptor.Level.NONE
                }
                // Never log the Authorization header
                redactHeader("Authorization")
            }

            val authInterceptor = AuthInterceptor(tokenManager)

            val okHttpClient = OkHttpClient.Builder()
                .addInterceptor(loggingInterceptor)
                .addInterceptor(authInterceptor)
                .addInterceptor { chain ->
                    val request = chain.request()
                    val response = chain.proceed(request)
                    if (response.code == 401) {
                        onUnauthorized()
                    }
                    response
                }
                .build()

            retrofit = Retrofit.Builder()
                .baseUrl(BASE_URL)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
        }
        return retrofit!!
    }

    fun getAuthApi(context: Context, onUnauthorized: () -> Unit): AuthApi {
        return getRetrofit(context, onUnauthorized).create(AuthApi::class.java)
    }

    fun getTelemetryApi(context: Context, onUnauthorized: () -> Unit = {}): TelemetryApi {
        return getRetrofit(context, onUnauthorized).create(TelemetryApi::class.java)
    }

    fun getTelemetryClient(context: Context, onUnauthorized: () -> Unit = {}): DjangoTelemetryClient {
        val tokenManager = SecureTokenManager(context)
        val api = getTelemetryApi(context, onUnauthorized)
        return DjangoTelemetryClient(api, tokenManager)
    }
}
