# 部署说明

## 环境要求

- Python 3.8+
- Node.js 16+
- SQLite 3

## 生产环境部署

### 后端部署

```bash
cd backend
pip install -r requirements.txt
# 设置环境变量
export SECRET_KEY="yXjiBi7GCQubdwBNL8axQSuRqILofUIbXZ022yCRzrE"
export UCLOUD_PUBLIC_KEY="4eZCt9GH5fS1XEutXeyTtv6A0QReFzqW5"
export UCLOUD_PRIVATE_KEY="9W5iDOdYn7cJxUaEgsYhMVCvhYR71fraGHpkmmJjuWmU"
# 使用Gunicorn启动
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 前端部署

```bash
cd admin-frontend
npm install
npm run build
# 将dist目录部署到Nginx或静态服务器
```

### Nginx配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        root /path/to/admin-frontend/dist;
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 数据库初始化

后端首次启动时会自动创建数据库表和初始数据。

## 定时任务

每分钟扣费任务在后端启动时自动运行。

## 客户端打包

```bash
cd client
pip install pyinstaller
pyinstaller --onefile --windowed main.py
```
