# AGENTS.md - 云电脑容器管理系统开发指南

本文件为AI编码助手提供项目规范，确保代码一致性。

## 项目结构

```
D:\traework\admin/
├── admin-frontend/       # Vue3后台管理
│   ├── src/
│   │   ├── api/         # API接口
│   │   ├── router/      # 路由配置
│   │   ├── stores/      # Pinia状态管理
│   │   └── views/       # 页面组件
│   └── vite.config.js   # Vite配置
├── backend/             # FastAPI后端
│   ├── app/
│   │   ├── api/        # 路由端点
│   │   ├── core/       # 核心配置
│   │   ├── db/         # 数据库
│   │   ├── models/     # SQLAlchemy模型
│   │   └── services/   # 业务逻辑
│   └── requirements.txt
├── client/             # PySide6客户端
├── test_api.py         # API测试
├── test_container_api.py  # 容器API测试
└── test_client.py      # 客户端测试
```

## 构建与运行命令

### 前端 (admin-frontend)
```bash
cd admin-frontend
npm install          # 安装依赖
npm run dev          # 开发服务器 (http://localhost:5173)
npm run build        # 生产构建
npm run preview      # 预览构建
```

### 后端 (backend)
```bash
cd backend
pip install -r requirements.txt   # 安装依赖
python run.py                     # 启动服务 (http://localhost:8000)
```

### 代码检查
```bash
# Python代码检查 (Ruff)
cd backend
ruff check .                      # 检查所有文件
ruff check app/models/user.py     # 检查单个文件
ruff check --fix .                # 自动修复问题

# Python代码格式化
ruff format .                     # 格式化所有文件
ruff format app/services/         # 格式化目录
```

### 测试命令
```bash
# 运行所有测试
python test_api.py
python test_container_api.py
python test_client.py

# 使用pytest运行单个测试（推荐）
pytest test_api.py -v                              # 详细输出
pytest test_api.py::test_create_container -v       # 运行单个测试函数
pytest test_container_api.py::TestContainer::test_list -v  # 运行单个测试类方法
pytest test_api.py -k "container"                  # 按名称过滤测试
```

## 代码风格指南

### Vue 3 / JavaScript
- **缩进**: 2空格
- **引号**: 单引号
- **分号**: 省略
- **API风格**: Composition API + `<script setup>`
- **状态管理**: Pinia (组合式API)
- **UI库**: Element Plus
- **路径别名**: `@/` 指向 `src/`

**导入排序:**
1. Vue核心库
2. 第三方库 (Element Plus, axios等)
3. 本地模块 (@/api, @/stores等)

**示例:**
```vue
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import { ElMessage } from 'element-plus'

const adminStore = useAdminStore()
const loading = ref(false)

const fetchData = async () => {
  loading.value = true
  try {
    // 业务逻辑
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>
```

### Python
- **缩进**: 4空格
- **引号**: 双引号
- **代码检查**: Ruff
- **类型提示**: 使用 `typing` 模块
- **异步**: 使用 `async/await` (FastAPI + SQLAlchemy 2.0)
- **模型**: SQLAlchemy声明式基类

**导入排序:**
1. 标准库
2. 第三方库
3. 本地模块 (app.*)

**示例:**
```python
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

class UserService:
    """用户服务"""

    @staticmethod
    async def get_by_id(
        db: AsyncSession, user_id: int
    ) -> Optional["User"]:
        """根据ID获取用户"""
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
```

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| Vue组件 | PascalCase | `UserList.vue` |
| JS变量/函数 | camelCase | `fetchData`, `userList` |
| Python类 | PascalCase | `UserService` |
| Python函数/变量 | snake_case | `get_by_id`, `user_data` |
| Python常量 | UPPER_SNAKE_CASE | `DEFAULT_PRICE` |
| API端点 | 小写+连字符 | `/admin/users` |

### 错误处理

**Vue:**
```javascript
const fetchData = async () => {
  loading.value = true
  try {
    const res = await api.get('/data')
    if (res.code === 200) {
      data.value = res.data
    }
  } catch (error) {
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}
```

**Python:**
```python
from fastapi import HTTPException

try:
    user = await user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
except Exception as e:
    logger.error(f"获取用户失败: {e}")
    raise HTTPException(status_code=500, detail="服务器错误")
```

### UI规范
- **主色调**: #409EFF
- **成功色**: #67C23A
- **警告色**: #E6A23C
- **危险色**: #F56C6C
- **侧边栏**: #304156
- **语言**: 中文界面，中文注释

### 组件模板规范
```vue
<template>
  <div class="page-name">
    <el-card>
      <template #header>
        <div class="header-actions">
          <span>页面标题</span>
          <el-button type="primary">操作</el-button>
        </div>
      </template>
      <!-- 内容 -->
    </el-card>
  </div>
</template>

<style scoped>
.page-name {
  padding: 20px;
}
.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
```

## 提交前检查清单

- [ ] 代码通过Ruff检查 (`ruff check .`)
- [ ] Python代码已格式化 (`ruff format .`)
- [ ] 没有console.log调试代码 (Vue)
- [ ] 错误处理完善
- [ ] 中文注释清晰
- [ ] 组件已scoped样式
- [ ] 新增API已在test_api.py测试
