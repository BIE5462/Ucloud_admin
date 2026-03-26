from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import get_settings

settings = get_settings()

# 创建异步引擎
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, future=True)

# 创建异步会话
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 声明基类
Base = declarative_base()

CONTAINER_RECORD_OPTIONAL_COLUMNS = {
    "config_code": "ALTER TABLE container_record ADD COLUMN config_code VARCHAR(50)",
    "config_name": "ALTER TABLE container_record ADD COLUMN config_name VARCHAR(100)",
}


async def get_db():
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await ensure_container_record_columns(conn)


async def ensure_container_record_columns(conn) -> None:
    """为旧版数据库补齐 container_record 缺失字段"""
    result = await conn.execute(
        text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='container_record'"
        )
    )
    if not result.scalar_one_or_none():
        return

    result = await conn.execute(text("PRAGMA table_info(container_record)"))
    existing_columns = {row[1] for row in result.fetchall()}

    for column_name, sql in CONTAINER_RECORD_OPTIONAL_COLUMNS.items():
        if column_name not in existing_columns:
            await conn.execute(text(sql))
