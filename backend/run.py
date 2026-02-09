import uvicorn
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import get_settings

settings = get_settings()

if __name__ == "__main__":
    print("=" * 50)
    print("云电脑容器管理系统 - 后端服务")
    print("=" * 50)
    print(f"服务地址: http://localhost:8000")
    print(f"API文档: http://localhost:8000/docs")
    print(f"调试模式: {settings.DEBUG}")
    print("=" * 50)
    print()

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
