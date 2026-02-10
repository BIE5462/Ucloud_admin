import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import init_db, AsyncSessionLocal, engine
from app.services.crud_service import admin_service, config_service
from app.core.security import get_password_hash
from app.core.config import get_settings
from app.models.models import (
    Base,
    User,
    Admin,
    ContainerRecord,
    BillingChargeRecord,
    BalanceLog,
    ContainerLog,
    SystemConfig,
    AdminOperationLog,
)
from sqlalchemy import text

settings = get_settings()


async def check_and_fix_container_table():
    """检查并修复 container_record 表结构（移除 user_id 唯一约束）"""
    print("检查 container_record 表结构...")

    async with engine.connect() as conn:
        # 检查表是否存在
        result = await conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='container_record'"
            )
        )
        if not result.scalar_one_or_none():
            print("  container_record 表不存在，将在初始化时创建")
            return

        # 检查是否有唯一约束
        result = await conn.execute(
            text(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='container_record'"
            )
        )
        table_sql = result.scalar_one_or_none()

        if table_sql and "UNIQUE (user_id)" in table_sql:
            print("  发现 user_id 唯一约束，正在重建表...")

            # 1. 备份数据
            result = await conn.execute(text("SELECT * FROM container_record"))
            rows = result.fetchall()
            columns = result.keys()
            print(f"  备份 {len(rows)} 条记录")

            # 2. 重命名旧表
            await conn.execute(
                text("ALTER TABLE container_record RENAME TO container_record_old")
            )

            # 3. 提交以确保重命名完成
            await conn.commit()

            # 4. 创建新表（使用模型定义，无唯一约束）
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(
                    bind=sync_conn, tables=[ContainerRecord.__table__]
                )
            )

            # 5. 恢复数据
            if rows:
                # 构建插入语句
                col_names = ", ".join(columns)
                placeholders = ", ".join(["?" for _ in columns])
                insert_sql = f"INSERT INTO container_record ({col_names}) VALUES ({placeholders})"

                for row in rows:
                    await conn.execute(text(insert_sql), tuple(row))

                print(f"  恢复 {len(rows)} 条记录")

            # 6. 删除旧表
            await conn.execute(text("DROP TABLE container_record_old"))

            await conn.commit()
            print("  表结构更新完成")
        else:
            print("  表结构正确，无需修改")


async def init_database():
    """初始化数据库"""
    print("正在初始化数据库...")

    # 先检查并修复表结构
    await check_and_fix_container_table()

    # 然后初始化其他表
    await init_db()
    print("数据库初始化完成")


async def clear_existing_data():
    """清除现有数据"""
    print("正在清除现有数据...")
    async with AsyncSessionLocal() as db:
        try:
            # 按照依赖关系顺序删除数据
            # 1. 删除日志表
            await db.execute(ContainerLog.__table__.delete())
            await db.execute(BalanceLog.__table__.delete())
            await db.execute(AdminOperationLog.__table__.delete())

            # 2. 删除计费记录
            await db.execute(BillingChargeRecord.__table__.delete())

            # 3. 删除容器记录
            await db.execute(ContainerRecord.__table__.delete())

            # 4. 删除用户记录
            await db.execute(User.__table__.delete())

            # 5. 删除系统配置
            await db.execute(SystemConfig.__table__.delete())

            # 6. 删除所有管理员账户
            await db.execute(Admin.__table__.delete())

            await db.commit()
            print("现有数据清除完成")
        except Exception as e:
            await db.rollback()
            print(f"清除数据失败: {e}")
            raise


async def create_default_data():
    """创建默认数据"""
    async with AsyncSessionLocal() as db:
        # 创建默认超级管理员
        print("创建默认超级管理员...")
        await admin_service.create(
            db, {"username": "admin", "password": "123456", "role": "super_admin"}
        )
        print("超级管理员创建成功")
        print("  用户名: admin")
        print("  密码: 123456")

        # 初始化系统配置
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


async def force_recreate_container_table():
    """强制重建 container_record 表（用于修复约束问题）"""
    print("强制重建 container_record 表...")

    async with engine.connect() as conn:
        # 检查表是否存在
        result = await conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='container_record'"
            )
        )
        if result.scalar_one_or_none():
            print("  删除旧表...")
            await conn.execute(text("DROP TABLE container_record"))
            await conn.commit()

        # 创建新表
        print("  创建新表...")
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                bind=sync_conn, tables=[ContainerRecord.__table__]
            )
        )
        print("  表重建完成")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="云电脑容器管理系统 - 数据库初始化")
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="强制重建 container_record 表（会丢失所有容器数据）",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("云电脑容器管理系统 - 初始化")
    print("=" * 50)

    if args.force_recreate:
        await force_recreate_container_table()
    else:
        await init_database()

    await clear_existing_data()
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
