package com.aerovital.phone.queue

import android.content.Context
import android.util.Log
import com.aerovital.phone.BuildConfig
import com.aerovital.shared.transport.TransportEnvelope
import com.google.gson.Gson
import java.io.File
import java.io.IOException
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.locks.ReentrantReadWriteLock
import kotlin.concurrent.read
import kotlin.concurrent.write

/**
 * Crash-safe, durable telemetry queue implementation backed by atomic filesystem operations.
 *
 * Durability guarantee:
 * - Each queue item is stored as an individual JSON file (`<messageId>.json`) in [storageDir].
 * - Writes are made to `<messageId>.tmp` and atomically renamed to `<messageId>.json`.
 * - Survives process death, application crashes, and device reboot.
 * - On startup/recreation, all existing records are reloaded from disk into memory.
 * - Confirmed deliveries remove the record from disk, preventing disk exhaustion.
 * - Failed terminal/blocked records remain on disk for inspection.
 */
class DurableTelemetryQueueStore(
    private val storageDir: File,
    private val gson: Gson = Gson(),
    private val retryPolicy: QueueRetryPolicy = QueueRetryPolicy()
) : TelemetryQueue {

    private val lock = ReentrantReadWriteLock()
    private val memoryIndex = ConcurrentHashMap<String, DurableQueueRecord>()

    init {
        if (!storageDir.exists()) {
            storageDir.mkdirs()
        }
        reloadFromDisk()
    }

    /**
     * Reads all existing records from the storage directory.
     */
    private fun reloadFromDisk() = lock.write {
        memoryIndex.clear()
        val files = storageDir.listFiles { file -> file.isFile && file.name.endsWith(".json") }
        if (files != null) {
            for (file in files) {
                try {
                    val json = file.readText(Charsets.UTF_8)
                    val record = gson.fromJson(json, DurableQueueRecord::class.java)
                    if (record != null && record.messageId.isNotBlank()) {
                        // Reset any record that was left IN_FLIGHT when the process died back to PENDING or FAILED_RETRYABLE
                        if (record.deliveryState == DeliveryState.IN_FLIGHT) {
                            record.deliveryState = if (record.attemptCount > 0) {
                                DeliveryState.FAILED_RETRYABLE
                            } else {
                                DeliveryState.PENDING
                            }
                        }
                        memoryIndex[record.messageId] = record
                    }
                } catch (e: Exception) {
                    if (BuildConfig.DEBUG) {
                        Log.e(TAG, "Corrupted queue file encountered: ${file.name}", e)
                    }
                    // Quarantine corrupted file to avoid repeated parse errors
                    val quarantined = File(storageDir, "${file.name}.corrupted")
                    file.renameTo(quarantined)
                }
            }
        }
    }

    override fun enqueue(envelope: TransportEnvelope): EnqueueResult = lock.write {
        if (memoryIndex.containsKey(envelope.messageId)) {
            return EnqueueResult.Duplicate(envelope.messageId)
        }

        if (memoryIndex.size >= retryPolicy.maxQueueCapacity) {
            return EnqueueResult.QueueFull(envelope.messageId, retryPolicy.maxQueueCapacity)
        }

        val record = DurableQueueRecord.fromTransportEnvelope(envelope)
        try {
            writeRecordToDisk(record)
            memoryIndex[record.messageId] = record
            EnqueueResult.Enqueued(record.messageId)
        } catch (e: IOException) {
            EnqueueResult.Rejected("Filesystem write failed: ${e.message}")
        }
    }

    override fun peekPending(limit: Int, currentEpochMs: Long): List<DurableQueueRecord> = lock.read {
        memoryIndex.values
            .filter { record ->
                when (record.deliveryState) {
                    DeliveryState.PENDING -> true
                    DeliveryState.FAILED_RETRYABLE -> {
                        val retryTime = record.nextRetryEpochMs
                        retryTime == null || retryTime <= currentEpochMs
                    }
                    else -> false
                }
            }
            .sortedWith(DurableQueueRecord.RECORD_ORDER_COMPARATOR)
            .take(limit)
    }

    override fun getRecord(messageId: String): DurableQueueRecord? = lock.read {
        memoryIndex[messageId]
    }

    override fun markInFlight(messageId: String): Boolean = lock.write {
        val record = memoryIndex[messageId] ?: return false
        record.deliveryState = DeliveryState.IN_FLIGHT
        try {
            writeRecordToDisk(record)
            true
        } catch (e: IOException) {
            false
        }
    }

    override fun markSuccess(messageId: String): Boolean = lock.write {
        memoryIndex.remove(messageId)
        val file = File(storageDir, "$messageId.json")
        if (file.exists()) {
            file.delete()
        } else {
            true
        }
    }

    override fun markRetryableFailure(
        messageId: String,
        classification: String,
        message: String?,
        delayMs: Long,
        attemptEpochMs: Long
    ): Boolean = lock.write {
        val record = memoryIndex[messageId] ?: return false
        record.attemptCount += 1
        record.lastAttemptEpochMs = attemptEpochMs
        record.nextRetryEpochMs = attemptEpochMs + delayMs
        record.deliveryState = DeliveryState.FAILED_RETRYABLE
        record.lastFailureClassification = classification
        record.lastFailureMessage = message
        try {
            writeRecordToDisk(record)
            true
        } catch (e: IOException) {
            false
        }
    }

    override fun markAuthBlocked(
        messageId: String,
        classification: String,
        message: String?,
        attemptEpochMs: Long
    ): Boolean = lock.write {
        val record = memoryIndex[messageId] ?: return false
        record.attemptCount += 1
        record.lastAttemptEpochMs = attemptEpochMs
        record.deliveryState = DeliveryState.AUTH_BLOCKED
        record.lastFailureClassification = classification
        record.lastFailureMessage = message
        try {
            writeRecordToDisk(record)
            true
        } catch (e: IOException) {
            false
        }
    }

    override fun markTerminalFailure(
        messageId: String,
        classification: String,
        message: String?,
        attemptEpochMs: Long
    ): Boolean = lock.write {
        val record = memoryIndex[messageId] ?: return false
        record.attemptCount += 1
        record.lastAttemptEpochMs = attemptEpochMs
        record.deliveryState = DeliveryState.FAILED_TERMINAL
        record.lastFailureClassification = classification
        record.lastFailureMessage = message
        try {
            writeRecordToDisk(record)
            true
        } catch (e: IOException) {
            false
        }
    }

    override fun countPending(): Int = lock.read {
        memoryIndex.values.count {
            it.deliveryState == DeliveryState.PENDING || it.deliveryState == DeliveryState.FAILED_RETRYABLE
        }
    }

    override fun countTotal(): Int = lock.read {
        memoryIndex.size
    }

    override fun getAllRecords(): List<DurableQueueRecord> = lock.read {
        memoryIndex.values.sortedWith(DurableQueueRecord.RECORD_ORDER_COMPARATOR)
    }

    override fun clear(): Unit = lock.write {
        memoryIndex.clear()
        storageDir.listFiles()?.forEach { it.delete() }
        Unit
    }

    /**
     * Atomically writes record to `<messageId>.tmp` and renames to `<messageId>.json`.
     */
    private fun writeRecordToDisk(record: DurableQueueRecord) {
        val json = gson.toJson(record)
        val tmpFile = File(storageDir, "${record.messageId}.tmp")
        val targetFile = File(storageDir, "${record.messageId}.json")

        tmpFile.writeText(json, Charsets.UTF_8)
        if (!tmpFile.renameTo(targetFile)) {
            // Fallback for filesystems where rename fails if target exists
            if (targetFile.exists()) {
                targetFile.delete()
            }
            if (!tmpFile.renameTo(targetFile)) {
                throw IOException("Atomic move failed from ${tmpFile.name} to ${targetFile.name}")
            }
        }
    }

    companion object {
        private const val TAG = "DurableTelemetryQueue"
        const val DEFAULT_DIR_NAME = "aerovital_telemetry_queue"

        /**
         * Factory method to create queue store backed by application's internal filesDir.
         */
        fun create(context: Context, retryPolicy: QueueRetryPolicy = QueueRetryPolicy()): DurableTelemetryQueueStore {
            val dir = File(context.filesDir, DEFAULT_DIR_NAME)
            return DurableTelemetryQueueStore(dir, Gson(), retryPolicy)
        }

        /**
         * Creates a store in a temporary directory (useful for headless testing or default fallback).
         */
        fun createTemporary(retryPolicy: QueueRetryPolicy = QueueRetryPolicy()): DurableTelemetryQueueStore {
            val baseDir = File(System.getProperty("java.io.tmpdir") ?: "/tmp")
            val dir = File(baseDir, "aerovital_test_queue_${System.nanoTime()}")
            return DurableTelemetryQueueStore(dir, Gson(), retryPolicy)
        }
    }
}
