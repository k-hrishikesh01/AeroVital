package com.aerovital.watch.transport

// Abstraction for testability
interface NodeProvider {
    suspend fun getConnectedNodeIds(): List<String>
}

interface MessageSender {
    suspend fun sendMessage(nodeId: String, path: String, data: ByteArray)
}
