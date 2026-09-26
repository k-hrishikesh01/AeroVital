package com.aerovital.watch.transport

import android.content.Context
import com.aerovital.shared.transport.ErrorReason
import com.aerovital.shared.transport.TransportEnvelope
import com.aerovital.shared.transport.TransportResult
import com.google.android.gms.wearable.Wearable
import com.google.gson.Gson
import kotlinx.coroutines.tasks.await

class WearTransportSender(
    private val nodeProvider: NodeProvider,
    private val messageSender: MessageSender,
    private val gson: Gson = Gson()
) {
    constructor(context: Context) : this(
        nodeProvider = object : NodeProvider {
            val nodeClient = Wearable.getNodeClient(context)
            override suspend fun getConnectedNodeIds(): List<String> {
                val nodes = nodeClient.connectedNodes.await()
                return nodes.map { it.id }
            }
        },
        messageSender = object : MessageSender {
            val messageClient = Wearable.getMessageClient(context)
            override suspend fun sendMessage(nodeId: String, path: String, data: ByteArray) {
                messageClient.sendMessage(nodeId, path, data).await()
            }
        }
    )

    /**
     * Retrieves currently connected node IDs (typically the paired phone).
     */
    suspend fun getConnectedNodeIds(): List<String> = nodeProvider.getConnectedNodeIds()

    suspend fun sendEnvelope(envelope: TransportEnvelope): TransportResult<Unit> {
        val validation = TransportEnvelope.validate(envelope, System.currentTimeMillis())
        if (validation is TransportResult.Error) {
            // For sending, we just check local validity, future/stale might not apply perfectly if the clock is weird
            // but it's safe to enforce the same core rules.
            return TransportResult.Error(validation.reason, validation.message)
        }

        try {
            val nodeIds = nodeProvider.getConnectedNodeIds()
            val phoneNodeId = nodeIds.firstOrNull()

            if (phoneNodeId == null) {
                return TransportResult.Error(ErrorReason.NO_NODES_CONNECTED, "No connected phone found")
            }

            val payloadBytes = gson.toJson(envelope).toByteArray(Charsets.UTF_8)
            messageSender.sendMessage(phoneNodeId, MESSAGE_PATH, payloadBytes)
            
            return TransportResult.Success(Unit)
        } catch (e: Exception) {
            return TransportResult.Error(ErrorReason.SEND_FAILED, e.message)
        }
    }

    companion object {
        const val MESSAGE_PATH = "/aerovital/telemetry/v1"
    }
}
