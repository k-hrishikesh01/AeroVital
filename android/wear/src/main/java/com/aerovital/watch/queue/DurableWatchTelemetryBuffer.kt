package com.aerovital.watch.queue

import android.content.Context
import android.util.Log
import com.aerovital.shared.transport.TransportEnvelope
import com.google.gson.Gson
import java.io.File
import java.io.IOException
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.locks.ReentrantReadWriteLock
import kotlin.concurrent.read
import kotlin.concurrent.write
import kotlin.math.min
import kotlin.math.pow

sealed class WatchEnqueueResult {
    data class Enqueued(val messageId: String) : WatchEnqueueResult()
    data class Duplicate(val messageId: String) : WatchEnqueueResult()
    data class OverflowEvictedOldest(val enqueuedMessageId: String, val evictedMessageId: String) : WatchEnqueueResult()
    data class Rejected(val reason: String) : WatchEnqueueResult()
}

/**
 * Crash-safe durable storage on the Wear OS device for telemetry batches.
 *
 * Guarantees:
 * - Each batch is written as an atomic file (<messageId>.tmp -> <messageId>.json).
 * - Batches are NEVER deleted when MessageClient.sendMessage completes.
 * - Batches are only removed when an explicit application ACK is received from the phone.
 * - Survives watch process death, background service restart, and device reboot.
 * - Enforces bounded storage capacity (maxCapacity) with safe oldest-drop overflow.
 * - Strict chronological ordering by sequence number and timestamp.
 * - Bounded exponential backoff on retries.
 */
class DurableWatchTelemetryBuffer(
    private val storageDir: File,
    private val gson: Gson = Gson(),
    val maxCapacity: Int = DEFAULT_MAX_CAPACITY,
    val baseRetryDelayMs: Long = DEFAULT_BASE_RETRY_DELAY_MS,
    val maxRetryDelayMs: Long = DEFAULT_MAX_RETRY_DELAY_MS,
    val maxRetryAttempts: Int = DEFAULT_MAX_RETRY_ATTEMPTS
) {
    private val lock = ReentrantReadWriteLock()
    private val memoryIndex = ConcurrentHashMap<String, WatchBatchRecord>()

    init {
        if (!storageDir.exists()) {
            storageDir.mkdirs()
        }
        reloadFromDisk()
    }

    /**
     * Reloads all pending unacknowledged records from disk.
     */
    fun reloadFromDisk() = lock.write {
        memoryIndex.clear()
        val files = storageDir.listFiles { file -> file.isFile && file.name.endsWith(".json") }
        if (files != null) {
            for (file in files) {
                try {
                    val json = file.readText(Charsets.UTF_8)
                    val record = gson.fromJson(json, WatchBatchRecord::class.java)
                    if (record != null && record.messageId.isNotBlank()) {
                        memoryIndex[record.messageId] = record
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Corrupted watch buffer file: ${file.name}", e)
                    val quarantined = File(storageDir, "${file.name}.corrupted")
                    file.renameTo(quarantined)
                }
            }
        }
        Log.i(TAG, "Watch buffer reloaded: ${memoryIndex.size} unacknowledged records on disk")
    }

    /**
     * Enqueues an envelope durably onto disk.
     */
    fun enqueue(envelope: TransportEnvelope): WatchEnqueueResult = lock.write {
        if (memoryIndex.containsKey(envelope.messageId)) {
            return WatchEnqueueResult.Duplicate(envelope.messageId)
        }

        var evictedId: String? = null
        if (memoryIndex.size >= maxCapacity) {
            // Safe bounded capacity handling: evict oldest unacknowledged batch
            val oldest = memoryIndex.values.minWithOrNull(WatchBatchRecord.CHRONOLOGICAL_COMPARATOR)
            if (oldest != null) {
                evictedId = oldest.messageId
                memoryIndex.remove(oldest.messageId)
                val oldFile = File(storageDir, "${oldest.messageId}.json")
                if (oldFile.exists()) oldFile.delete()
                Log.w(TAG, "Watch buffer capacity ($maxCapacity) reached; evicted oldest messageId=$evictedId")
            }
        }

        val record = WatchBatchRecord.fromEnvelope(envelope, gson)
        return try {
            writeRecordToDisk(record)
            memoryIndex[record.messageId] = record
            if (evictedId != null) {
                WatchEnqueueResult.OverflowEvictedOldest(record.messageId, evictedId)
            } else {
                WatchEnqueueResult.Enqueued(record.messageId)
            }
        } catch (e: IOException) {
            WatchEnqueueResult.Rejected("Failed writing to watch disk: ${e.message}")
        }
    }

    /**
     * Peeks unacknowledged pending records ready for transmission,
     * ordered strictly chronologically by sequence number and timestamp.
     */
    fun peekPending(limit: Int = 10, currentEpochMs: Long = System.currentTimeMillis()): List<WatchBatchRecord> = lock.read {
        memoryIndex.values
            .filter { record ->
                !record.isAcknowledged && (record.nextRetryEpochMs == null || record.nextRetryEpochMs!! <= currentEpochMs)
            }
            .sortedWith(WatchBatchRecord.CHRONOLOGICAL_COMPARATOR)
            .take(limit)
    }

    /**
     * Confirms application-level delivery from phone ACK.
     * Atomically removes the confirmed batch from disk and memory.
     */
    fun markAcknowledged(messageId: String): Boolean = lock.write {
        val removed = memoryIndex.remove(messageId) != null
        val file = File(storageDir, "$messageId.json")
        if (file.exists()) {
            file.delete()
        }
        if (removed) {
            Log.d(TAG, "Batch $messageId acknowledged by phone; evicted from durable watch buffer")
        }
        removed
    }

    /**
     * Marks transmission failure with bounded exponential backoff.
     * When Bluetooth is disconnected, we do NOT consume attempt count so expected out-of-range
     * periods do not dead-letter valid observations.
     */
    fun markTransmissionFailure(
        messageId: String,
        isLinkConnected: Boolean,
        currentEpochMs: Long = System.currentTimeMillis()
    ): Boolean = lock.write {
        val record = memoryIndex[messageId] ?: return false
        record.lastAttemptEpochMs = currentEpochMs

        if (!isLinkConnected) {
            // Disconnected: do not penalize attempt count or block immediate replay upon reconnection
            record.nextRetryEpochMs = null
        } else {
            // Link is connected but send failed (e.g. transport error)
            record.attemptCount += 1
            val delayMs = computeBackoffDelay(record.attemptCount)
            record.nextRetryEpochMs = currentEpochMs + delayMs
        }

        try {
            writeRecordToDisk(record)
            true
        } catch (e: IOException) {
            false
        }
    }

    fun countPending(): Int = lock.read {
        memoryIndex.values.count { !it.isAcknowledged }
    }

    fun countTotal(): Int = lock.read {
        memoryIndex.size
    }

    fun getRecord(messageId: String): WatchBatchRecord? = lock.read {
        memoryIndex[messageId]
    }

    fun clear(): Unit = lock.write {
        memoryIndex.clear()
        storageDir.listFiles()?.forEach { it.delete() }
    }

    private fun computeBackoffDelay(attempt: Int): Long {
        val factor = 2.0.pow((attempt - 1).coerceAtLeast(0).toDouble()).toLong()
        val computed = baseRetryDelayMs * factor
        return min(computed, maxRetryDelayMs)
    }

    private fun writeRecordToDisk(record: WatchBatchRecord) {
        val json = gson.toJson(record)
        val tmpFile = File(storageDir, "${record.messageId}.tmp")
        val targetFile = File(storageDir, "${record.messageId}.json")

        tmpFile.writeText(json, Charsets.UTF_8)
        if (!tmpFile.renameTo(targetFile)) {
            if (targetFile.exists()) {
                targetFile.delete()
            }
            if (!tmpFile.renameTo(targetFile)) {
                throw IOException("Atomic rename failed from ${tmpFile.name} to ${targetFile.name}")
            }
        }
    }

    companion object {
        private const val TAG = "WatchTelemetryBuffer"
        const val DEFAULT_DIR_NAME = "aerovital_watch_buffer"
        const val DEFAULT_MAX_CAPACITY = 500 // 500 batches ~ 40+ minutes of 5s batches
        const val DEFAULT_BASE_RETRY_DELAY_MS = 2000L
        const val DEFAULT_MAX_RETRY_DELAY_MS = 30000L
        const val DEFAULT_MAX_RETRY_ATTEMPTS = 10

        fun create(context: Context): DurableWatchTelemetryBuffer {
            val dir = File(context.filesDir, DEFAULT_DIR_NAME)
            return DurableWatchTelemetryBuffer(dir)
        }

        fun createTemporary(): DurableWatchTelemetryBuffer {
            val baseDir = File(System.getProperty("java.io.tmpdir") ?: "/tmp")
            val dir = File(baseDir, "aerovital_watch_test_${System.nanoTime()}")
            return DurableWatchTelemetryBuffer(dir)
        }
    }
}
