package com.aerovital.phone.transport

import android.content.Context
import android.util.Log
import com.aerovital.phone.BuildConfig
import com.aerovital.shared.transport.TelemetryAck
import com.aerovital.shared.transport.TransportEnvelope
import com.google.android.gms.wearable.Wearable
import kotlinx.coroutines.tasks.await

/**
 * Sends explicit application-level acknowledgements to the Wear OS device
 * once telemetry batches are safely stored in the phone's durable queue.
 */
interface PhoneAckSender {
    suspend fun sendAck(nodeId: String, ack: TelemetryAck): Boolean
}

class DefaultPhoneAckSender(private val context: Context) : PhoneAckSender {
    override suspend fun sendAck(nodeId: String, ack: TelemetryAck): Boolean {
        return try {
            val messageClient = Wearable.getMessageClient(context)
            val ackBytes = ack.toJson().toByteArray(Charsets.UTF_8)
            messageClient.sendMessage(nodeId, TransportEnvelope.ACK_PATH, ackBytes).await()
            if (BuildConfig.DEBUG) {
                Log.d(TAG, "Dispatched application ACK for messageId=${ack.messageId} to node $nodeId")
            }
            true
        } catch (e: Exception) {
            Log.w(TAG, "Failed to dispatch ACK for messageId=${ack.messageId} to node $nodeId: ${e.message}")
            false
        }
    }

    companion object {
        private const val TAG = "PhoneAckSender"
    }
}
