import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
import core.config as config

from core.collector_engine import CollectorEngine
from services.orchestrator import Orchestrator, ConnectionManager
from web.api.collectors import router as collectors_router
from web.api.settings import router as settings_router
from web.pages.dashboard import router as dashboard_router

# 載入環境變數
load_dotenv('.env')

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 初始化核心組件
app = FastAPI(title="StockHunter Pro - Dashboard")
controller = CollectorEngine()
ws_manager = ConnectionManager()
task_service = Orchestrator(controller, ws_manager)

# 設置日誌級別
logging.getLogger("uvicorn.access").setLevel(getattr(logging, config.LOG_LEVEL))

# 注入依賴
collectors_router.controller = controller
collectors_router.task_status = task_service.task_status
collectors_router.background_runner = task_service.background_collector_runner

# 掛載路由
app.include_router(dashboard_router)
app.include_router(settings_router)
app.include_router(collectors_router)

@app.get("/api/status")
async def get_status():
    return controller.get_system_status()

@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_running_loop()
    task_service.set_loop(loop)
    logger.info(f"🚀 StockHunter Dashboard started at http://{config.WEB_HOST}:{config.WEB_PORT}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json({"type": "init", "data": task_service.task_status})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.WEB_HOST, port=config.WEB_PORT)
