package com.aerovital.watch.transport

import android.util.Log
import com.aerovital.shared.transport.TelemetryAck
import com.aerovital.shared.transport.TransportEnvelope
import com.google.android.gms.wearable.MessageEvent
import com.google.android.gms.wearable.WearableListenerService

/**
 * Background listener service for receiving explicit phone acknowledgements
 * when telemetry batches are stored in the phone's durable queue.
 */
class WatchAckListenerService : WearableListenerService() {

    override fun onMessageReceived(messageEvent: MessageEvent) {
        super.onMessageReceived(messageEvent)

        if (messageEvent.path == TransportEnvelope.ACK_PATH) {
            val json = String(messageEvent.data, Charsets.UTF_8)
            val ack = TelemetryAck.fromJson(json)
            if (ack != null) {
                Log.d(TAG, "Received ACK for messageId=${ack.messageId}, status=${ack.status}")
                ackHandler?.invoke(ack)
            }
        }
    }

    companion object {
        private const val TAG = "WatchAckListener"

        @Volatile
        var ackHandler: ((TelemetryAck) -> Unit)? = null
    }
}
