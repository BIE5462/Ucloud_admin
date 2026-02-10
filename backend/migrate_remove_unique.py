"""
数据库迁移脚本：移除 container_record 表 user_id 字段的唯一约束

SQLite 不支持直接删除列约束，因此需要通过创建新表的方式实现：
1. 创建新表 container_record_new（结构同原表，但 user_id 不带 UNIQUE 约束）
2. 将旧表数据复制到新表
3. 删除旧表
4. 重命名新表为 container_record
5. 重建索引 ix_container_record_id
"""

import asyncio
from sqlalchemy import text
from app.db.database import engine


async def migrate_remove_user_id_unique():
    """移除 container_record 表 user_id 字段的唯一约束"""

    async with engine.begin() as conn:
        print("开始迁移：移除 container_record.user_id 的唯一约束")

        # 1. 创建新表（不带 UNIQUE 约束的 user_id）
        print("步骤 1: 创建新表 container_record_new...")
        await conn.execute(
            text("""
            CREATE TABLE container_record_new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ucloud_instance_id VARCHAR(100) NOT NULL,
                instance_name VARCHAR(100) NOT NULL,
                status VARCHAR(20) DEFAULT 'creating',
                gpu_type VARCHAR(50) NOT NULL,
                cpu_cores INTEGER NOT NULL,
                memory_gb INTEGER NOT NULL,
                storage_gb INTEGER NOT NULL,
                price_per_minute FLOAT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                started_at DATETIME,
                stopped_at DATETIME,
                deleted_at DATETIME,
                total_running_minutes INTEGER DEFAULT 0,
                total_cost FLOAT DEFAULT 0.0,
                connection_host VARCHAR(100),
                connection_port INTEGER DEFAULT 3389,
                connection_username VARCHAR(50),
                connection_password VARCHAR(100),
                FOREIGN KEY(user_id) REFERENCES m_user (id)
            )
        """)
        )
        print("  ✓ 新表创建完成")

        # 2. 复制数据
        print("步骤 2: 复制数据到新表...")
        await conn.execute(
            text("""
            INSERT INTO container_record_new (
                id, user_id, ucloud_instance_id, instance_name, status,
                gpu_type, cpu_cores, memory_gb, storage_gb, price_per_minute,
                created_at, started_at, stopped_at, deleted_at,
                total_running_minutes, total_cost,
                connection_host, connection_port, connection_username, connection_password
            )
            SELECT 
                id, user_id, ucloud_instance_id, instance_name, status,
                gpu_type, cpu_cores, memory_gb, storage_gb, price_per_minute,
                created_at, started_at, stopped_at, deleted_at,
                total_running_minutes, total_cost,
                connection_host, connection_port, connection_username, connection_password
            FROM container_record
        """)
        )

        # 获取复制行数
        result = await conn.execute(text("SELECT COUNT(*) FROM container_record_new"))
        count = result.scalar()
        print(f"  ✓ 复制了 {count} 条记录")

        # 3. 删除旧表
        print("步骤 3: 删除旧表 container_record...")
        await conn.execute(text("DROP TABLE container_record"))
        print("  ✓ 旧表删除完成")

        # 4. 重命名新表
        print("步骤 4: 重命名新表为 container_record...")
        await conn.execute(
            text("ALTER TABLE container_record_new RENAME TO container_record")
        )
        print("  ✓ 重命名完成")

        # 5. 重建索引 ix_container_record_id
        print("步骤 5: 重建索引 ix_container_record_id...")
        await conn.execute(
            text("CREATE INDEX ix_container_record_id ON container_record (id)")
        )
        print("  ✓ 索引重建完成")

        print("\n迁移完成：container_record.user_id 的唯一约束已移除")


async def verify_migration():
    """验证迁移结果"""
    async with engine.begin() as conn:
        # 检查索引
        result = await conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='container_record'"
            )
        )
        indexes = [row[0] for row in result.fetchall()]
        print(f"\n验证结果:")
        print(f"  container_record 表索引: {indexes}")

        # 检查表结构（检查 user_id 列）
        result = await conn.execute(text("PRAGMA table_info(container_record)"))
        columns = result.fetchall()
        user_id_col = None
        for col in columns:
            if col[1] == "user_id":
                user_id_col = col
                break

        if user_id_col:
            print(f"  user_id 列信息: {user_id_col}")
            print(f"  唯一约束已移除: {not user_id_col[5]} (pk={user_id_col[5]})")


if __name__ == "__main__":
    asyncio.run(migrate_remove_user_id_unique())
    asyncio.run(verify_migration())
