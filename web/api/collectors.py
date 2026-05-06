from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["Data Collection"])

class RunTaskRequest(BaseModel):
    collector_ids: List[int]
    use_custom_range: bool = False
    start_date: Optional[str] = None
    end_date: Optional[str] = None

# 這些會由 server.py 在包含 router 時透過 app.state 或依賴注入提供
# 但為了簡單，我們假設 server.py 會正確配置這些

@router.get("/collectors")
async def get_collectors(controller=Depends(lambda: router.controller)):
    return controller.get_available_collectors()

@router.post("/run")
async def run_tasks(
    request: RunTaskRequest, 
    background_tasks: BackgroundTasks,
    controller=Depends(lambda: router.controller),
    task_status=Depends(lambda: router.task_status),
    background_runner=Depends(lambda: router.background_runner)
):
    if task_status["is_running"]:
        raise HTTPException(status_code=400, detail="已有任務正在執行中")
    
    background_tasks.add_task(
        background_runner, 
        request.collector_ids, 
        request.use_custom_range,
        request.start_date,
        request.end_date
    )
    return {"status": "started", "message": f"已啟動 {len(request.collector_ids)} 個任務"}
