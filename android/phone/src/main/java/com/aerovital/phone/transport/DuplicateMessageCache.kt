package com.aerovital.phone.transport

import java.util.Collections
import java.util.LinkedHashMap

class DuplicateMessageCache(private val maxCapacity: Int) {
    // LinkedHashMap with accessOrder = false (insertion order), overriding removeEldestEntry to bound it
    private val cacheMap = object : LinkedHashMap<String, Long>(maxCapacity, 0.75f, false) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<String, Long>?): Boolean {
            return size > maxCapacity
        }
    }
    
    private val syncMap = Collections.synchronizedMap(cacheMap)

    /**
     * Adds the messageId to the cache if not present.
     * @return true if added (was not seen), false if it was already in the cache (is a duplicate).
     */
    fun addIfNotSeen(messageId: String): Boolean {
        synchronized(syncMap) {
            if (syncMap.containsKey(messageId)) {
                return false
            }
            syncMap[messageId] = System.currentTimeMillis()
            return true
        }
    }
    
    fun clear() {
        syncMap.clear()
    }
}
