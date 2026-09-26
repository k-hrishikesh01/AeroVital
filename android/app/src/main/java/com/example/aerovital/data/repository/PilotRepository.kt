package com.example.aerovital.data.repository

import com.example.aerovital.data.model.FlightSession
import com.example.aerovital.data.model.PilotProfile
import com.google.firebase.firestore.FirebaseFirestore
import kotlinx.coroutines.tasks.await
import java.util.concurrent.ConcurrentHashMap

class PilotRepository {

    private val firestore: FirebaseFirestore? by lazy {
        try {
            FirebaseFirestore.getInstance()
        } catch (e: Exception) {
            null
        }
    }

    // Local fallback database for robust offline & standalone operation
    private val localPilots = ConcurrentHashMap<String, PilotProfile>()
    private val localHistory = ConcurrentHashMap<String, MutableList<FlightSession>>()

    init {
        // Seed initial pilot data if local cache is used
        val demoPilot = PilotProfile(
            pilotId = "AVP-2026-001",
            fullName = "Ananya V",
            recoveryEmail = "avp2026001@aerovital.internal",
            authUid = "demo_uid_001",
            createdAt = System.currentTimeMillis(),
            status = "ACTIVE"
        )
        localPilots[demoPilot.pilotId] = demoPilot

        val demoSessions = mutableListOf(
            FlightSession(
                id = "session_001",
                date = "2026-09-24",
                duration = "02:45:32",
                sScore = "78%",
                conferenceScore = "50%",
                condition = "NORMAL",
                heartRate = "78 BPM",
                fatigueState = "Low"
            ),
            FlightSession(
                id = "session_002",
                date = "2026-09-22",
                duration = "01:30:15",
                sScore = "82%",
                conferenceScore = "65%",
                condition = "NORMAL",
                heartRate = "72 BPM",
                fatigueState = "Optimal"
            )
        )
        localHistory[demoPilot.pilotId] = demoSessions
    }

    suspend fun checkPilotExists(pilotId: String): Boolean {
        val db = firestore
        if (db != null) {
            try {
                val doc = db.collection("pilots").document(pilotId).get().await()
                if (doc.exists()) return true
            } catch (e: Exception) {
                // Fallback to local check
            }
        }
        return localPilots.containsKey(pilotId)
    }

    suspend fun savePilotProfile(profile: PilotProfile): Result<Unit> {
        localPilots[profile.pilotId] = profile
        val db = firestore
        if (db != null) {
            try {
                db.collection("pilots").document(profile.pilotId).set(profile).await()
            } catch (e: Exception) {
                // Local save succeeded
            }
        }
        return Result.success(Unit)
    }

    suspend fun getPilotProfile(pilotId: String): PilotProfile? {
        val db = firestore
        if (db != null) {
            try {
                val doc = db.collection("pilots").document(pilotId).get().await()
                if (doc.exists()) {
                    val profile = doc.toObject(PilotProfile::class.java)
                    if (profile != null) {
                        localPilots[pilotId] = profile
                        return profile
                    }
                }
            } catch (e: Exception) {
                // Fall through to local
            }
        }
        return localPilots[pilotId]
    }

    suspend fun getFlightHistory(pilotId: String): List<FlightSession> {
        val db = firestore
        if (db != null) {
            try {
                val snapshot = db.collection("pilots")
                    .document(pilotId)
                    .collection("history")
                    .get()
                    .await()

                val sessions = snapshot.documents.mapNotNull { it.toObject(FlightSession::class.java) }
                if (sessions.isNotEmpty()) {
                    localHistory[pilotId] = sessions.toMutableList()
                    return sessions
                }
            } catch (e: Exception) {
                // Fall through to local
            }
        }
        return localHistory[pilotId] ?: emptyList()
    }
}
