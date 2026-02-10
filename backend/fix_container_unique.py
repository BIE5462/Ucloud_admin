#!/usr/bin/env python3
"""
数据库迁移脚本：移除 container_record 表的 user_id 唯一约束
"""

import sqlite3
import os


def migrate():
    db_path = os.path.join(os.path.dirname(__file__), "cloud_pc.db")

    if not os.path.exists(db_path):
        print(f"错误：数据库文件不存在 {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. 检查 container_record 表是否存在
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='container_record'"
        )
        if not cursor.fetchone():
            print("错误：container_record 表不存在")
            return

        # 2. 检查是否有 user_id 的唯一约束
        cursor.execute("PRAGMA index_list('container_record')")
        indexes = cursor.fetchall()

        has_unique_constraint = False
        for index in indexes:
            # index: (seq, name, unique, origin, partial, seqno)
            index_name = index[1]
            is_unique = index[2]

            if is_unique:
                cursor.execute(f"PRAGMA index_info('{index_name}')")
                index_info = cursor.fetchall()
                for info in index_info:
                    # info: (seqno, cid, name)
                    if info[2] == "user_id":
                        has_unique_constraint = True
                        print(f"发现 user_id 唯一约束: {index_name}")
                        break

        if not has_unique_constraint:
            print("container_record 表没有 user_id 的唯一约束，无需迁移")
            return

        print("开始执行迁移...")

        # 3. 获取表的完整结构
        cursor.execute("PRAGMA table_info('container_record')")
        columns = cursor.fetchall()

        # 4. 获取外键约束
        cursor.execute("PRAGMA foreign_key_list('container_record')")
        foreign_keys = cursor.fetchall()

        # 5. 构建创建新表的 SQL
        column_defs = []
        for col in columns:
            # col: (cid, name, type, notnull, default_value, pk)
            cid, name, col_type, notnull, default_val, pk = col
            col_def = f"{name} {col_type}"
            if pk:
                col_def += " PRIMARY KEY"
            if notnull:
                col_def += " NOT NULL"
            if default_val is not None:
                col_def += f" DEFAULT {default_val}"
            column_defs.append(col_def)

        # 6. 创建新表（不带唯一约束）
        create_sql = f"""
        CREATE TABLE container_record_new (
            {", ".join(column_defs)}
        )
        """
        cursor.execute(create_sql)
        print("创建新表 container_record_new 成功")

        # 7. 复制数据
        column_names = [col[1] for col in columns]
        columns_str = ", ".join(column_names)
        cursor.execute(
            f"INSERT INTO container_record_new ({columns_str}) SELECT {columns_str} FROM container_record"
        )
        copied_count = cursor.rowcount
        print(f"复制了 {copied_count} 条数据到新表")

        # 8. 删除旧表
        cursor.execute("DROP TABLE container_record")
        print("删除旧表 container_record 成功")

        # 9. 重命名新表
        cursor.execute("ALTER TABLE container_record_new RENAME TO container_record")
        print("重命名新表为 container_record 成功")

        # 10. 重建索引（排除 user_id 的唯一索引）
        cursor.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='container_record'"
        )
        old_indexes = cursor.fetchall()

        for idx_name, idx_sql in old_indexes:
            # 跳过 sqlite 自动创建的索引
            if idx_name.startswith("sqlite_"):
                continue
            # 跳过包含 user_id 唯一约束的索引
            if (
                "user_id" in (idx_sql or "").lower()
                and "UNIQUE" in (idx_sql or "").upper()
            ):
                print(f"跳过 user_id 唯一索引: {idx_name}")
                continue
            if idx_sql:
                # 替换表名
                new_sql = idx_sql.replace("container_record", "container_record_new", 1)
                new_sql = new_sql.replace("container_record_new", "container_record", 1)
                try:
                    cursor.execute(new_sql)
                    print(f"重建索引: {idx_name}")
                except sqlite3.Error as e:
                    print(f"重建索引 {idx_name} 失败: {e}")

        conn.commit()
        print("\n迁移完成！")

        # 11. 验证
        cursor.execute("PRAGMA index_list('container_record')")
        new_indexes = cursor.fetchall()
        print("\n当前索引列表：")
        for idx in new_indexes:
            print(f"  - {idx[1]} (唯一: {bool(idx[2])})")

    except sqlite3.Error as e:
        conn.rollback()
        print(f"迁移失败: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
