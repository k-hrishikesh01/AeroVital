from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import asyncio
import json

from backend.app.core.models import TelemetryData, FatigueResult
from backend.app.fatigue.engine import FatigueEngine

app = FastAPI(title="AeroVital API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State (In-memory for MVP)
latest_telemetry: Optional[TelemetryData] = None
latest_fatigue: Optional[FatigueResult] = None
fatigue_engine = FatigueEngine()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/v1/status")
def get_status():
    return {
        "engine_active": True,
        "latest_telemetry_time": latest_telemetry.timestamp if latest_telemetry else None,
        "latest_fatigue_state": latest_fatigue.fatigue_state if latest_fatigue else None
    }

@app.post("/api/v1/telemetry", response_model=FatigueResult)
async def post_telemetry(telemetry: TelemetryData):
    global latest_telemetry, latest_fatigue
    
    latest_telemetry = telemetry
    
    # Process through fatigue engine
    result = fatigue_engine.evaluate(telemetry)
    latest_fatigue = result
    
    # Broadcast to websocket clients
    await manager.broadcast({
        "type": "update",
        "telemetry": telemetry.model_dump(mode='json'),
        "fatigue": result.model_dump(mode='json')
    })
    
    return result

@app.get("/api/v1/telemetry/latest", response_model=Optional[TelemetryData])
def get_latest_telemetry():
    return latest_telemetry

@app.get("/api/v1/fatigue/latest", response_model=Optional[FatigueResult])
def get_latest_fatigue():
    return latest_fatigue

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial state if available
        if latest_telemetry and latest_fatigue:
            await websocket.send_json({
                "type": "update",
                "telemetry": latest_telemetry.model_dump(mode='json'),
                "fatigue": latest_fatigue.model_dump(mode='json')
            })
            
        while True:
            # Just keep connection alive, we don't expect client messages
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
