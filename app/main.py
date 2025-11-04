from http.client import responses

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import uuid
from contextlib import asynccontextmanager

from core.config import settings
from core.logger import setup_logging, get_logger
from core.database import init_db, close_db
from app.api.v1.endpoints.auth import auth_router
setup_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Task Management API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    await init_db()
    logger.info("✅ Database initialized")

    yield

    logger.info(" Shutting down Task Management API")
    await close_db()
    logger.info("Database connections closed")


app = FastAPI(
    title=settings.project_name,
    description="A real-time collaborative task management API",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,  # Disable docs in production
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)
app.include_router(auth_router)

@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):

    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    logger.info(
        f"Incoming request: {request.method} {request.url.path}",
        extra={"request_id": request_id}
    )

    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    logger.info(
        f"Request completed: {request.method} {request.url.path} | "
        f"Status: {response.status_code} | Duration: {duration:.3f}s",
        extra={"request_id": request_id}
    )

    return response

@app.middleware("http")
async def log_errors_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        request_id = getattr(request.state, "request_id", "unknown")

        logger.exception(
            f"Unhandled exception: {str(e)}",
            extra={"request_id": request_id},
            exc_info=True
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "detail": str(e) if settings.debug else "An unexpected error occurred",
                "request_id": request_id
            }
        )




app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    logger.debug("Root endpoint accessed")
    return {
        "message": "Task Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    logger.debug("Health check endpoint accessed")
    return {
        "status": "healthy",
        "environment": settings.environment,
        "timestamp": time.time()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    logger.debug("Health check endpoint accessed")
    return {
        "status": "healthy",
        "environment": settings.environment,
        "timestamp": time.time()
    }
