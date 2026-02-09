# 云电脑容器管理系统

基于UCloud GPU云电脑服务的容器管理系统，支持按需计费、1:1用户绑定、持久化实例管理。

## 项目结构

```
cloud-pc-manager/
├── backend/              # FastAPI后端服务
│   ├── app/             # 应用代码
│   ├── requirements.txt # Python依赖
│   └── run.py           # 启动脚本
├── admin-frontend/      # Vue3后台管理
│   ├── src/             # 源代码
│   ├── package.json     # Node依赖
│   └── vite.config.js   # Vite配置
└── client/              # PySide6客户端
    ├── main.py          # 客户端入口
    └── requirements.txt # Python依赖
```

## 技术栈

| 模块 | 技术 |
|------|------|
| 后端 | Python + FastAPI + SQLAlchemy + SQLite |
| 后台管理 | Vue 3 + Vite + Element Plus |
| 客户端 | Python + PySide6 |
| 认证 | JWT（PyJWT） |
| 云服务商 | UCloud SDK |

## 核心功能

- **容器管理**：基于UCloud的GPU云电脑服务
- **按需计费**：按实际运行时长计费，每分钟自动扣费
- **1:1绑定**：一个用户绑定一个云电脑实例
- **持久化实例**：关机后保留实例状态和数据
- **日志记录**：完整的操作日志和扣费记录追踪
- **权限管理**：超级管理员 + 管理员 + 用户三级权限

## 快速开始

### 1. 启动后端服务

```bash
cd backend
pip install -r requirements.txt
python run.py
```

后端服务将在 http://localhost:8000 启动

### 2. 启动后台管理

```bash
cd admin-frontend
npm install
npm run dev
```

后台管理将在 http://localhost:5173 启动

### 3. 启动客户端

```bash
cd client
pip install -r requirements.txt
python main.py
```

## 默认账号

- **超级管理员**: admin / Admin123@
- **管理员**: 通过超级管理员创建
- **用户**: 通过管理员创建

## API文档

启动后端后访问: http://localhost:8000/docs

## 许可证

MIT
