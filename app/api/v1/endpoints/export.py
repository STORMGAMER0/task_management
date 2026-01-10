from fastapi import APIRouter, Depends, Query, Response, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Optional
from celery.result import AsyncResult
import base64
import io

from models.user import User
from models.task import TaskStatus, TaskPriority
from app.api.dependencies import get_current_user
from tasks.export import export_tasks_csv, export_tasks_pdf
from core.celery_app import celery_app

export_router = APIRouter(prefix="/tasks/export", tags=["Task Export"])


@export_router.get("/csv", status_code=status.HTTP_202_ACCEPTED)
async def export_tasks_to_csv(
        status_filter: Optional[TaskStatus] = Query(None, alias="status"),
        priority: Optional[TaskPriority] = Query(None),
        assigned_to: Optional[str] = Query(None),
        current_user: User = Depends(get_current_user)
):


    filters = {}
    if status_filter:
        filters['status'] = status_filter.value
    if priority:
        filters['priority'] = priority.value
    if assigned_to:
        filters['assigned_to'] = assigned_to


    task = export_tasks_csv.delay(str(current_user.id), filters)

    return {
        "task_id": task.id,
        "status": "processing",
        "message": "Export is being generated. Use task_id to check status.",
        "check_status_url": f"/api/v1/tasks/export/status/{task.id}"
    }


@export_router.get("/pdf", status_code=status.HTTP_202_ACCEPTED)
async def export_tasks_to_pdf(
        status_filter: Optional[TaskStatus] = Query(None, alias="status"),
        priority: Optional[TaskPriority] = Query(None),
        assigned_to: Optional[str] = Query(None),
        current_user: User = Depends(get_current_user)
):

    filters = {}
    if status_filter:
        filters['status'] = status_filter.value
    if priority:
        filters['priority'] = priority.value
    if assigned_to:
        filters['assigned_to'] = assigned_to


    task = export_tasks_pdf.delay(str(current_user.id), filters)

    return {
        "task_id": task.id,
        "status": "processing",
        "message": "Export is being generated. Use task_id to check status.",
        "check_status_url": f"/api/v1/tasks/export/status/{task.id}"
    }


@export_router.get("/status/{task_id}")
async def check_export_status(
        task_id: str,
        current_user: User = Depends(get_current_user)
):

    result = AsyncResult(task_id, app=celery_app)

    if result.ready():
        if result.successful():
            task_result = result.result
            return {
                "task_id": task_id,
                "status": "SUCCESS",
                "result": {
                    "task_count": task_result.get("task_count"),
                    "filename": task_result.get("filename"),
                    "download_url": f"/api/v1/tasks/export/download/{task_id}"
                }
            }
        else:
            return {
                "task_id": task_id,
                "status": "FAILURE",
                "error": str(result.info)
            }
    else:
        return {
            "task_id": task_id,
            "status": "PENDING",
            "message": "Export is still being generated. Please check again in a few seconds."
        }


@export_router.get("/download/{task_id}")
async def download_export(
        task_id: str,
        current_user: User = Depends(get_current_user)
):

    result = AsyncResult(task_id, app=celery_app)

    if not result.ready():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Export is still processing. Check status first."
        )

    if not result.successful():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {result.info}"
        )

    task_result = result.result
    filename = task_result.get("filename")

    # Determine file type from result
    if "csv_content" in task_result:
        # CSV download
        content = task_result["csv_content"]
        media_type = "text/csv"

        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    elif "pdf_content" in task_result:
        # PDF download
        pdf_base64 = task_result["pdf_content"]
        pdf_bytes = base64.b64decode(pdf_base64)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Export result format not recognized"
        )