#!/bin/bash

# 云电脑容器管理系统 - 环境安装配置脚本
# 用法: chmod +x install.sh && ./install.sh

set -e

echo "=========================================="
echo "  云电脑容器管理系统 - 环境安装脚本"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 安装 Node.js 20+ (如果未安装)
install_nodejs() {
    echo -e "${YELLOW}[1/6] 检查 Node.js 20+...${NC}"
    
    if command_exists node && command_exists npm; then
        NODE_VERSION=$(node --version)
        NPM_VERSION=$(npm --version)
        
        # 提取版本号数字部分
        VERSION=$(echo "$NODE_VERSION" | sed 's/v//')
        MAJOR=$(echo "$VERSION" | cut -d '.' -f 1)
        
        if [ "$MAJOR" -ge 20 ]; then
            echo -e "${GREEN}✓ Node.js 20+ 已安装: $NODE_VERSION${NC}"
            echo -e "${GREEN}✓ npm 已安装: $NPM_VERSION${NC}"
        else
            echo -e "${YELLOW}Node.js 版本过低: $NODE_VERSION，需要 20+，正在安装...${NC}"
            
            # 检测Linux发行版
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                OS=$NAME
            else
                echo -e "${RED}无法检测操作系统${NC}"
                exit 1
            fi
            
            # 根据发行版安装 Node.js
            case "$OS" in
                "Ubuntu"*|"Debian"*) 
                    # 先卸载旧版本
                    sudo apt-get remove -y nodejs npm
                    sudo apt-get autoremove -y
                    # 安装新版本
                    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
                    sudo apt-get install -y nodejs
                    ;;
                "CentOS"*|"Red Hat"*|"Fedora"*) 
                    # 先卸载旧版本
                    sudo yum remove -y nodejs npm
                    # 安装新版本
                    curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
                    sudo yum install -y nodejs
                    ;;
                "Arch Linux") 
                    sudo pacman -S nodejs npm --noconfirm
                    ;;
                *)
                    echo -e "${RED}不支持的操作系统: $OS${NC}"
                    echo "请手动安装 Node.js 20+"
                    exit 1
                    ;;
            esac
            
            echo -e "${GREEN}✓ Node.js 20+ 安装完成${NC}"
        fi
    else
        echo -e "${YELLOW}Node.js 未安装，正在安装...${NC}"
        
        # 检测Linux发行版
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$NAME
        else
            echo -e "${RED}无法检测操作系统${NC}"
            exit 1
        fi
        
        # 根据发行版安装 Node.js
        case "$OS" in
            "Ubuntu"*|"Debian"*) 
                curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
                sudo apt-get install -y nodejs
                ;;
            "CentOS"*|"Red Hat"*|"Fedora"*) 
                curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
                sudo yum install -y nodejs
                ;;
            "Arch Linux") 
                sudo pacman -S nodejs npm --noconfirm
                ;;
            *)
                echo -e "${RED}不支持的操作系统: $OS${NC}"
                echo "请手动安装 Node.js 20+"
                exit 1
                ;;
        esac
        
        echo -e "${GREEN}✓ Node.js 安装完成${NC}"
    fi
    echo ""
}

# 安装 Python 3.12 (如果未安装)
install_python() {
    echo -e "${YELLOW}[2/6] 检查 Python 3.12...${NC}"
    
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version)
        # Extract major and minor version
        VERSION=$(echo "$PYTHON_VERSION" | awk '{print $2}')
        MAJOR=$(echo "$VERSION" | cut -d '.' -f 1)
        MINOR=$(echo "$VERSION" | cut -d '.' -f 2)
        
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -eq 12 ]; then
            echo -e "${GREEN}✓ Python 3.12 已安装: $PYTHON_VERSION${NC}"
        else
            echo -e "${YELLOW}Python 3.12 未安装，当前版本: $PYTHON_VERSION，正在安装...${NC}"
            
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                OS=$NAME
            fi
            
            case "$OS" in
                "Ubuntu"*|"Debian"*) 
                    sudo apt-get update
                    sudo apt-get install -y software-properties-common
                    sudo add-apt-repository -y ppa:deadsnakes/ppa
                    sudo apt-get update
                    sudo apt-get install -y python3.12 python3.12-pip python3.12-venv
                    ;;
                "CentOS"*|"Red Hat"*|"Fedora"*) 
                    sudo yum install -y python3.12 python3.12-pip
                    ;;
                "Arch Linux") 
                    sudo pacman -S python python-pip --noconfirm
                    ;;
                *)
                    echo -e "${RED}不支持的操作系统: $OS${NC}"
                    echo "请手动安装 Python 3.12"
                    exit 1
                    ;;
            esac
            
            echo -e "${GREEN}✓ Python 3.12 安装完成${NC}"
        fi
    else
        echo -e "${YELLOW}Python3 未安装，正在安装 Python 3.12...${NC}"
        
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$NAME
        fi
        
        case "$OS" in
            "Ubuntu"*|"Debian"*) 
                sudo apt-get update
                sudo apt-get install -y software-properties-common
                sudo add-apt-repository -y ppa:deadsnakes/ppa
                sudo apt-get update
                sudo apt-get install -y python3.12 python3.12-pip python3.12-venv
                ;;
            "CentOS"*|"Red Hat"*|"Fedora"*) 
                sudo yum install -y python3.12 python3.12-pip
                ;;
            "Arch Linux") 
                sudo pacman -S python python-pip --noconfirm
                ;;
            *)
                echo -e "${RED}不支持的操作系统: $OS${NC}"
                echo "请手动安装 Python 3.12"
                exit 1
                ;;
        esac
        
        echo -e "${GREEN}✓ Python 3.12 安装完成${NC}"
    fi
    echo ""
}

# 安装前端依赖
install_frontend_deps() {
    echo -e "${YELLOW}[3/6] 安装前端依赖...${NC}"
    
    cd "$SCRIPT_DIR/admin-frontend"
    
    if [ ! -d "node_modules" ]; then
        echo "正在安装 npm 依赖，请稍候..."
        npm install
        echo -e "${GREEN}✓ 前端依赖安装完成${NC}"
    else
        echo -e "${GREEN}✓ 前端依赖已存在${NC}"
    fi
    
    cd "$SCRIPT_DIR"
    echo ""
}

# 安装后端依赖
install_backend_deps() {
    echo -e "${YELLOW}[4/6] 安装后端依赖...${NC}"
    
    cd "$SCRIPT_DIR/backend"
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        echo "创建 Python 虚拟环境..."
        python3.12 -m venv venv
        echo -e "${GREEN}✓ 虚拟环境创建完成${NC}"
    fi
    
    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    
    echo "安装 Python 依赖..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo -e "${GREEN}✓ 后端依赖安装完成${NC}"
    
    cd "$SCRIPT_DIR"
    echo ""
}

# 安装客户端依赖
install_client_deps() {
    echo -e "${YELLOW}[5/6] 安装客户端依赖...${NC}"
    
    cd "$SCRIPT_DIR/client"
    
    # 使用后端相同的虚拟环境或创建新的
    if [ ! -d "venv" ]; then
        echo "创建 Python 虚拟环境..."
        python3.12 -m venv venv
        echo -e "${GREEN}✓ 虚拟环境创建完成${NC}"
    fi
    
    source venv/bin/activate
    
    echo "安装 Python 依赖..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo -e "${GREEN}✓ 客户端依赖安装完成${NC}"
    
    cd "$SCRIPT_DIR"
    echo ""
}

# 创建必要的数据库目录
setup_database() {
    echo -e "${YELLOW}[6/6] 设置数据库...${NC}"
    
    # 创建数据库目录
    mkdir -p "$SCRIPT_DIR/backend/data"
    
    echo -e "${GREEN}✓ 数据库目录已创建${NC}"
    echo ""
}

# 主函数
main() {
    echo "开始安装配置环境..."
    echo ""
    
    install_nodejs
    install_python
    install_frontend_deps
    install_backend_deps
    install_client_deps
    setup_database
    
    echo "=========================================="
    echo -e "${GREEN}  环境安装配置完成！${NC}"
    echo "=========================================="
    echo ""
    echo "使用说明:"
    echo "  1. 开发模式启动: ./start.sh"
    echo "  2. 前端地址: http://localhost:5173"
    echo "  3. 后端地址: http://localhost:8000"
    echo "  4. API文档: http://localhost:8000/docs"
    echo ""
}

# 运行主函数
main
