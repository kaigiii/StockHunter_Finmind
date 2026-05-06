from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import os

router = APIRouter(tags=["dashboard"])

@router.get("/", response_class=HTMLResponse)
async def index():
    ui_path = "ui/dashboard.html"
    if os.path.exists(ui_path):
        with open(ui_path, "r", encoding="utf-8") as f:
            return f.read()
    return "UI file not found. Please check ui/dashboard.html"

# We'll let the main app or a specific router handle controller-dependent stats
