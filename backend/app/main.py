import traceback
import uuid
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.core.config import get_settings
from app.db.database import init_db
from app.tasks.scheduler import start_scheduler, shutdown_scheduler
from app.api import (
    auth,
    container,
    billing,
    admin_user,
    admin_manager,
    admin_config,
    admin_dashboard,
)

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    await init_db()
    start_scheduler()
    yield
    # 关闭时清理
    shutdown_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    description="云电脑容器管理系统API",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(container.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(admin_user.router, prefix="/api")
app.include_router(admin_manager.router, prefix="/api")
app.include_router(admin_config.router, prefix="/api")
app.include_router(admin_dashboard.router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "云电脑容器管理系统API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ==================== 全局异常处理器 ====================


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    """添加请求上下文信息"""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    request.state.timestamp = datetime.now().isoformat()

    response = await call_next(request)

    # 添加请求ID到响应头
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理HTTP异常"""
    request_id = getattr(request.state, "request_id", "unknown")

    error_response = {
        "code": exc.status_code,
        "message": exc.detail,
        "data": None,
        "request_id": request_id,
        "timestamp": datetime.now().isoformat(),
        "error_type": "http_exception",
        "path": str(request.url),
    }

    logger.error(
        f"HTTP异常 [{request_id}] {exc.status_code}: {exc.detail} - {request.url}"
    )

    return JSONResponse(status_code=exc.status_code, content=error_response)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理通用异常"""
    request_id = getattr(request.state, "request_id", "unknown")
    error_traceback = traceback.format_exc()

    error_response = {
        "code": 500,
        "message": "服务器内部错误",
        "data": None,
        "request_id": request_id,
        "timestamp": datetime.now().isoformat(),
        "error_type": "internal_server_error",
        "path": str(request.url),
        "detail": {
            "error_class": exc.__class__.__name__,
            "error_message": str(exc),
            "traceback": error_traceback.split("\n") if settings.DEBUG else None,
        },
    }

    logger.error(
        f"未处理异常 [{request_id}] {exc.__class__.__name__}: {str(exc)}\n{error_traceback}"
    )

    return JSONResponse(status_code=500, content=error_response)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start_time = datetime.now()
    request_id = getattr(request.state, "request_id", "unknown")

    logger.info(f"→ 请求 [{request_id}] {request.method} {request.url}")

    try:
        response = await call_next(request)
        duration = (datetime.now() - start_time).total_seconds()

        logger.info(f"← 响应 [{request_id}] {response.status_code} - {duration:.3f}s")
        return response
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(
            f"✕ 异常 [{request_id}] {e.__class__.__name__}: {str(e)} - {duration:.3f}s"
        )
        raise
