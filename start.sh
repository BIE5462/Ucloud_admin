#!/bin/bash

# 云电脑容器管理系统 - 一键启动脚本
# 用法: chmod +x start.sh && ./start.sh
# 选项:
#   ./start.sh          - 启动前端和后端
#   ./start.sh frontend - 仅启动前端
#   ./start.sh backend  - 仅启动后端
#   ./start.sh client   - 仅启动客户端

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 存储后台进程ID
FRONTEND_PID=""
BACKEND_PID=""
CLIENT_PID=""

# 清理函数 - 退出时终止所有子进程
cleanup() {
    echo ""
    echo -e "${YELLOW}正在停止所有服务...${NC}"
    
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        echo -e "${GREEN}✓ 前端服务已停止${NC}"
    fi
    
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        echo -e "${GREEN}✓ 后端服务已停止${NC}"
    fi
    
    if [ -n "$CLIENT_PID" ]; then
        kill $CLIENT_PID 2>/dev/null || true
        echo -e "${GREEN}✓ 客户端已停止${NC}"
    fi
    
    echo -e "${GREEN}所有服务已停止${NC}"
    exit 0
}

# 捕获退出信号
trap cleanup SIGINT SIGTERM EXIT

# 启动前端服务
start_frontend() {
    echo -e "${BLUE}[前端]${NC} 正在启动前端服务..."
    
    cd "$SCRIPT_DIR/admin-frontend"
    
    # 检查node_modules是否存在
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}[前端]${NC} 依赖未安装，正在安装..."
        npm install
    fi
    
    # 后台启动前端服务
    npm run dev > "$SCRIPT_DIR/logs/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    
    echo -e "${GREEN}[前端]${NC} 服务已启动 (PID: $FRONTEND_PID)"
    echo -e "${GREEN}[前端]${NC} 地址: http://localhost:5173"
    echo ""
}

# 启动后端服务
start_backend() {
    echo -e "${BLUE}[后端]${NC} 正在启动后端服务..."
    
    cd "$SCRIPT_DIR/backend"
    
    # 检查虚拟环境是否存在
    if [ ! -d "venv" ]; then
        echo -e "${RED}[后端]${NC} 虚拟环境不存在，请先运行 ./install.sh${NC}"
        exit 1
    fi
    
    # 激活虚拟环境并启动
    source venv/bin/activate
    
    # 后台启动后端服务
    python run.py > "$SCRIPT_DIR/logs/backend.log" 2>&1 &
    BACKEND_PID=$!
    
    echo -e "${GREEN}[后端]${NC} 服务已启动 (PID: $BACKEND_PID)"
    echo -e "${GREEN}[后端]${NC} 地址: http://localhost:8000"
    echo -e "${GREEN}[后端]${NC} API文档: http://localhost:8000/docs"
    echo ""
}

# 启动客户端
start_client() {
    echo -e "${BLUE}[客户端]${NC} 正在启动客户端..."
    
    cd "$SCRIPT_DIR/client"
    
    # 检查虚拟环境是否存在
    if [ ! -d "venv" ]; then
        echo -e "${RED}[客户端]${NC} 虚拟环境不存在，请先运行 ./install.sh${NC}"
        exit 1
    fi
    
    # 激活虚拟环境并启动
    source venv/bin/activate
    
    # 后台启动客户端
    python main.py > "$SCRIPT_DIR/logs/client.log" 2>&1 &
    CLIENT_PID=$!
    
    echo -e "${GREEN}[客户端]${NC} 已启动 (PID: $CLIENT_PID)"
    echo ""
}

# 显示帮助信息
show_help() {
    echo "云电脑容器管理系统 - 一键启动脚本"
    echo ""
    echo "用法:"
    echo "  ./start.sh           启动前端和后端服务"
    echo "  ./start.sh frontend  仅启动前端服务"
    echo "  ./start.sh backend   仅启动后端服务"
    echo "  ./start.sh client    仅启动客户端"
    echo "  ./start.sh all       启动前端、后端和客户端"
    echo ""
}

# 等待服务启动
wait_for_services() {
    echo -e "${YELLOW}等待服务启动...${NC}"
    sleep 3
    
    # 检查前端
    if [ -n "$FRONTEND_PID" ]; then
        if kill -0 $FRONTEND_PID 2>/dev/null; then
            echo -e "${GREEN}✓ 前端服务运行正常${NC}"
        else
            echo -e "${RED}✗ 前端服务启动失败，请检查日志: logs/frontend.log${NC}"
        fi
    fi
    
    # 检查后端
    if [ -n "$BACKEND_PID" ]; then
        if kill -0 $BACKEND_PID 2>/dev/null; then
            echo -e "${GREEN}✓ 后端服务运行正常${NC}"
        else
            echo -e "${RED}✗ 后端服务启动失败，请检查日志: logs/backend.log${NC}"
        fi
    fi
    
    # 检查客户端
    if [ -n "$CLIENT_PID" ]; then
        if kill -0 $CLIENT_PID 2>/dev/null; then
            echo -e "${GREEN}✓ 客户端运行正常${NC}"
        else
            echo -e "${RED}✗ 客户端启动失败，请检查日志: logs/client.log${NC}"
        fi
    fi
    
    echo ""
}

# 主函数
main() {
    # 创建日志目录
    mkdir -p "$SCRIPT_DIR/logs"
    
    echo "=========================================="
    echo "  云电脑容器管理系统 - 一键启动"
    echo "=========================================="
    echo ""
    
    # 解析参数
    MODE=${1:-default}
    
    case "$MODE" in
        "frontend")
            start_frontend
            ;;
        "backend")
            start_backend
            ;;
        "client")
            start_client
            ;;
        "all")
            start_frontend
            start_backend
            start_client
            ;;
        "help"|"-h"|"--help")
            show_help
            exit 0
            ;;
        *)
            # 默认启动前端和后端
            start_frontend
            start_backend
            ;;
    esac
    
    wait_for_services
    
    echo "=========================================="
    echo -e "${GREEN}  所有服务已启动！${NC}"
    echo "=========================================="
    echo ""
    
    if [ -n "$FRONTEND_PID" ]; then
        echo -e "前端地址: ${BLUE}http://localhost:5173${NC}"
    fi
    
    if [ -n "$BACKEND_PID" ]; then
        echo -e "后端地址: ${BLUE}http://localhost:8000${NC}"
        echo -e "API文档:  ${BLUE}http://localhost:8000/docs${NC}"
    fi
    
    echo ""
    echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"
    echo ""
    
    # 等待用户中断
    wait
}

# 运行主函数
main "$@"
