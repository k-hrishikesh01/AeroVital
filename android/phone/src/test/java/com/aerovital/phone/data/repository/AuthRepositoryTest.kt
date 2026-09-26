package com.aerovital.phone.data.repository

import com.aerovital.phone.data.model.auth.AuthRequest
import com.aerovital.phone.data.remote.AuthApi
import com.aerovital.phone.data.remote.AuthInterceptor
import com.aerovital.phone.data.remote.TokenManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

@OptIn(ExperimentalCoroutinesApi::class)
class AuthRepositoryTest {

    private lateinit var mockWebServer: MockWebServer
    private lateinit var authApi: AuthApi
    private lateinit var fakeTokenManager: FakeTokenManager
    private lateinit var repository: AuthRepository

    private val testDispatcher = StandardTestDispatcher()

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        mockWebServer = MockWebServer()
        mockWebServer.start()

        fakeTokenManager = FakeTokenManager()

        val okHttpClient = OkHttpClient.Builder()
            .addInterceptor(AuthInterceptor(fakeTokenManager))
            .build()

        authApi = Retrofit.Builder()
            .baseUrl(mockWebServer.url("/"))
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AuthApi::class.java)

        repository = AuthRepository(authApi, fakeTokenManager)
    }

    @After
    fun tearDown() {
        mockWebServer.shutdown()
        Dispatchers.resetMain()
    }
    
    @Test
    fun `TokenManager fake behaves correctly`() {
        assertNull(fakeTokenManager.getToken())
        fakeTokenManager.saveToken("my-token")
        assertEquals("my-token", fakeTokenManager.getToken())
        fakeTokenManager.clearToken()
        assertNull(fakeTokenManager.getToken())
    }

    @Test
    fun `login request sends correct contract and updates state on success`() = runTest {
        val successResponse = """
            {
                "token": "fake-token-123",
                "user_id": 1,
                "username": "testpilot",
                "pilot": {
                    "id": "uuid-123",
                    "pilot_code": "P-001",
                    "name": "Test Pilot",
                    "age": 30,
                    "sex": "M",
                    "is_active": true,
                    "created_at": "2023-01-01T00:00:00Z",
                    "updated_at": "2023-01-01T00:00:00Z"
                }
            }
        """.trimIndent()
        
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(successResponse))

        repository.login(AuthRequest("testpilot", "password123"))

        // Verify request contract
        val request = mockWebServer.takeRequest()
        assertEquals("POST", request.method)
        assertEquals("/api/v1/auth/token/", request.path)
        assertTrue(request.getHeader("Content-Type")?.contains("application/json") == true)
        val body = request.body.readUtf8()
        assertTrue(body.contains("\"username\":\"testpilot\""))
        assertTrue(body.contains("\"password\":\"password123\""))
        assertNull(request.getHeader("Authorization")) // Ensure no auth header on login

        // Verify state updates
        val state = repository.authState.value
        assertTrue(state is AuthState.Authenticated)
        assertEquals("fake-token-123", fakeTokenManager.getToken())
        val authState = state as AuthState.Authenticated
        assertEquals("testpilot", authState.username)
        assertEquals("Test Pilot", authState.pilot?.name)
    }

    @Test
    fun `login with invalid credentials returns 401 error state`() = runTest {
        val errorResponse = """{"detail": "Invalid credentials."}"""
        mockWebServer.enqueue(MockResponse().setResponseCode(401).setBody(errorResponse))

        repository.login(AuthRequest("wrong", "wrong"))

        val state = repository.authState.value
        assertTrue(state is AuthState.Error)
        assertEquals(ErrorType.INVALID_CREDENTIALS, (state as AuthState.Error).type)
    }

    @Test
    fun `fetchMe request uses token and updates profile`() = runTest {
        fakeTokenManager.saveToken("test-token-456")
        
        val successResponse = """
            {
                "user_id": 1,
                "username": "testpilot",
                "email": "test@test.com",
                "pilot": {
                    "id": "uuid-123",
                    "pilot_code": "P-001",
                    "name": "Fetched Pilot",
                    "age": 30,
                    "sex": "M",
                    "is_active": true,
                    "created_at": "2023-01-01T00:00:00Z",
                    "updated_at": "2023-01-01T00:00:00Z"
                }
            }
        """.trimIndent()
        
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody(successResponse))

        repository.fetchMe()

        // Verify request contract
        val request = mockWebServer.takeRequest()
        assertEquals("GET", request.method)
        assertEquals("/api/v1/auth/me/", request.path)
        assertEquals("Token test-token-456", request.getHeader("Authorization"))

        // Verify state updates
        val state = repository.authState.value
        assertTrue(state is AuthState.Authenticated)
        val authState = state as AuthState.Authenticated
        assertEquals("Fetched Pilot", authState.pilot?.name)
    }

    @Test
    fun `fetchMe returns 401 clears session`() = runTest {
        fakeTokenManager.saveToken("expired-token")
        mockWebServer.enqueue(MockResponse().setResponseCode(401))

        repository.fetchMe()

        val state = repository.authState.value
        assertTrue(state is AuthState.Error)
        assertEquals(ErrorType.SESSION_INVALID, (state as AuthState.Error).type)
        assertNull(fakeTokenManager.getToken())
    }

    @Test
    fun `logout requests server and clears local state`() = runTest {
        fakeTokenManager.saveToken("existing-token")
        mockWebServer.enqueue(MockResponse().setResponseCode(200).setBody("""{"detail": "Successfully logged out."}"""))

        repository.logout()

        val request = mockWebServer.takeRequest()
        assertEquals("POST", request.method)
        assertEquals("/api/v1/auth/logout/", request.path)
        assertEquals("Token existing-token", request.getHeader("Authorization"))

        val state = repository.authState.value
        assertTrue(state is AuthState.Unauthenticated)
        assertEquals(null, fakeTokenManager.getToken())
    }

    @Test
    fun `logout network failure still clears local state`() = runTest {
        fakeTokenManager.saveToken("existing-token")
        mockWebServer.enqueue(MockResponse().setSocketPolicy(okhttp3.mockwebserver.SocketPolicy.DISCONNECT_AT_START))

        repository.logout()

        val state = repository.authState.value
        assertTrue(state is AuthState.Unauthenticated)
        assertEquals(null, fakeTokenManager.getToken())
    }
}

class FakeTokenManager : TokenManager {
    private var token: String? = null
    override fun saveToken(t: String) { token = t }
    override fun getToken(): String? = token
    override fun clearToken() { token = null }
}
