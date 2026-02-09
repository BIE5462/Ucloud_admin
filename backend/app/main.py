from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

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
