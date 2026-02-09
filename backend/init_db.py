import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import init_db, AsyncSessionLocal
from app.services.crud_service import admin_service, config_service
from app.core.security import get_password_hash
from app.core.config import get_settings

settings = get_settings()


async def init_database():
    """初始化数据库"""
    print("正在初始化数据库...")
    await init_db()
    print("数据库初始化完成")


async def create_default_data():
    """创建默认数据"""
    async with AsyncSessionLocal() as db:
        # 检查是否已有超级管理员
        admin = await admin_service.get_by_username(db, "admin")
        if not admin:
            print("创建默认超级管理员...")
            await admin_service.create(
                db, {"username": "admin", "password": "Admin123@@", "role": "super_admin"}
            )
            print("超级管理员创建成功")
            print("  用户名: admin")
            print("  密码: Admin123@")

        # 初始化系统配置
        configs = await config_service.get_all_configs(db)
        if "price_per_minute" not in configs:
            print("初始化系统配置...")
            await config_service.set_config(
                db,
                "price_per_minute",
                str(settings.DEFAULT_PRICE_PER_MINUTE),
                description="云电脑每分钟价格（元）",
            )
            await config_service.set_config(
                db,
                "min_balance_to_start",
                str(settings.DEFAULT_MIN_BALANCE_TO_START),
                description="启动云电脑所需最低余额",
            )
            await config_service.set_config(
                db, "auto_stop_threshold", "0.0", description="自动停止余额阈值"
            )
            print("系统配置初始化完成")

        print("\n默认配置:")
        print(f"  每分钟价格: {settings.DEFAULT_PRICE_PER_MINUTE} 元")
        print(f"  启动最低余额: {settings.DEFAULT_MIN_BALANCE_TO_START} 元")


async def main():
    """主函数"""
    print("=" * 50)
    print("云电脑容器管理系统 - 初始化")
    print("=" * 50)

    await init_database()
    await create_default_data()

    print("\n" + "=" * 50)
    print("初始化完成！")
    print("=" * 50)
    print("\n启动服务:")
    print("  python run.py")
    print("\nAPI文档地址:")
    print("  http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())
