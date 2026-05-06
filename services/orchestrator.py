import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Set, Dict
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except:
                self.active_connections.remove(connection)

class Orchestrator:
    def __init__(self, controller, manager: ConnectionManager):
        self.controller = controller
        self.manager = manager
        self.task_status = {
            "is_running": False,
            "last_message": "系統就緒",
            "history": []
        }
        self.loop = None

    def set_loop(self, loop):
        self.loop = loop

    def background_collector_runner(self, collector_ids: List[int], use_custom_range: bool, 
                                   start_date: Optional[str] = None, end_date: Optional[str] = None):
        """背景執行收集任務"""
        self.task_status["is_running"] = True
        self.task_status["history"] = []
        
        def ui_callback(message, level="info"):
            now = datetime.now().strftime("%H:%M:%S")
            self.task_status["last_message"] = message
            log_entry = {"time": now, "msg": message, "level": level}
            self.task_status["history"].append(log_entry)
            
            if self.loop:
                asyncio.run_coroutine_threadsafe(self.manager.broadcast({"type": "log", "data": log_entry}), self.loop)
            
            if len(self.task_status["history"]) > 100:
                self.task_status["history"].pop(0)

        try:
            for result in self.controller.run_collectors(collector_ids, use_custom_range, start_date, end_date):
                if not isinstance(result, dict): continue
                
                m_type = result.get("type")
                m_text = result.get("msg", "")
                
                if m_type == "log":
                    ui_callback(m_text, result.get("level", "info"))
                elif m_type == "wait":
                    ui_callback(f"⏳ {m_text}", "info")
                elif m_type == "summary":
                    ui_callback(f"📊 {m_text}", "success")
                    self.task_status["last_message"] = f"✅ {m_text}"
            
        except Exception as e:
            error_msg = f"❌ 執行異常: {str(e)}"
            ui_callback(error_msg, "error")
            logger.error(f"Background task error: {e}")
        finally:
            self.task_status["is_running"] = False
            if self.loop:
                asyncio.run_coroutine_threadsafe(self.manager.broadcast({"type": "status", "data": self.task_status}), self.loop)
