#!/bin/bash

echo "========================================"
echo "云电脑容器管理系统 - 一键启动脚本"
echo "========================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 启动后端服务
echo "[1/3] 正在启动后端服务..."
cd "$SCRIPT_DIR/backend"
python3 run.py &
BACKEND_PID=$!

sleep 3

# 启动前端服务
echo "[2/3] 正在启动后台管理前端..."
cd "$SCRIPT_DIR/admin-frontend"
npm run dev &
FRONTEND_PID=$!

sleep 3

# 显示信息
echo ""
echo "========================================"
echo "服务启动完成！"
echo "========================================"
echo ""
echo "访问地址:"
echo "  后端API:   http://localhost:8000"
echo "  API文档:   http://localhost:8000/docs"
echo "  后台管理:  http://localhost:5173"
echo ""
echo "默认管理员账号:"
echo "  用户名: admin"
echo "  密码: Admin123@"
echo ""
echo "客户端启动:"
echo "  cd client && python3 main.py"
echo ""
echo "========================================"
echo "按 Ctrl+C 停止所有服务"
echo "========================================"

# 等待用户中断
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
