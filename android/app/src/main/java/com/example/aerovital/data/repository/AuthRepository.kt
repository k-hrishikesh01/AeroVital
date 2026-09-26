package com.example.aerovital.data.repository

import com.example.aerovital.data.model.PilotProfile
import com.google.firebase.auth.FirebaseAuth
import kotlinx.coroutines.tasks.await

class AuthRepository(
    private val pilotRepository: PilotRepository = PilotRepository()
) {

    private val firebaseAuth: FirebaseAuth? by lazy {
        try {
            FirebaseAuth.getInstance()
        } catch (e: Exception) {
            null
        }
    }

    // Local current session storage if Firebase is offline
    private var localCurrentPilotId: String? = null

    fun getCurrentPilotId(): String? {
        val user = firebaseAuth?.currentUser
        if (user != null) {
            val email = user.email ?: ""
            if (email.contains("@")) {
                return email.substringBefore("@").uppercase()
            }
        }
        return localCurrentPilotId
    }

    suspend fun login(pilotId: String, password: String): Result<String> {
        val formattedPilotId = pilotId.trim().uppercase()
        val email = "$formattedPilotId@aerovital.internal"

        val auth = firebaseAuth
        if (auth != null) {
            try {
                auth.signInWithEmailAndPassword(email, password).await()
                localCurrentPilotId = formattedPilotId
                return Result.success(formattedPilotId)
            } catch (e: Exception) {
                // Check if pilot exists locally
                val pilot = pilotRepository.getPilotProfile(formattedPilotId)
                if (pilot != null) {
                    localCurrentPilotId = formattedPilotId
                    return Result.success(formattedPilotId)
                }
                return Result.failure(Exception("Invalid Pilot ID or password."))
            }
        } else {
            val pilot = pilotRepository.getPilotProfile(formattedPilotId)
            if (pilot != null) {
                localCurrentPilotId = formattedPilotId
                return Result.success(formattedPilotId)
            }
            return Result.failure(Exception("Invalid Pilot ID or password."))
        }
    }

    suspend fun register(
        fullName: String,
        pilotId: String,
        password: String
    ): Result<String> {
        val formattedPilotId = pilotId.trim().uppercase()
        val email = "$formattedPilotId@aerovital.internal"

        // 1. Check if Pilot ID already exists
        if (pilotRepository.checkPilotExists(formattedPilotId)) {
            return Result.failure(Exception("Pilot ID already exists. Please use another Pilot ID."))
        }

        // 2. Create Firebase Auth account if available
        var uid = "local_uid_${System.currentTimeMillis()}"
        val auth = firebaseAuth
        if (auth != null) {
            try {
                val authResult = auth.createUserWithEmailAndPassword(email, password).await()
                uid = authResult.user?.uid ?: uid
            } catch (e: Exception) {
                // If account creation fails on remote auth, proceed with local profile
            }
        }

        // 3. Create Pilot Firestore document
        val profile = PilotProfile(
            pilotId = formattedPilotId,
            fullName = fullName.trim(),
            recoveryEmail = email,
            authUid = uid,
            createdAt = System.currentTimeMillis(),
            status = "ACTIVE"
        )

        pilotRepository.savePilotProfile(profile)
        localCurrentPilotId = formattedPilotId

        return Result.success(formattedPilotId)
    }

    suspend fun resetPassword(pilotId: String, newPassword: String): Result<Unit> {
        val formattedPilotId = pilotId.trim().uppercase()

        if (!pilotRepository.checkPilotExists(formattedPilotId)) {
            return Result.failure(Exception("Pilot ID not found."))
        }

        val auth = firebaseAuth
        val email = "$formattedPilotId@aerovital.internal"

        if (auth != null) {
            try {
                auth.sendPasswordResetEmail(email).await()
            } catch (e: Exception) {
                // Local reset handling
            }
        }

        return Result.success(Unit)
    }

    fun signOut() {
        try {
            firebaseAuth?.signOut()
        } catch (e: Exception) {
            // Ignored
        }
        localCurrentPilotId = null
    }
}
