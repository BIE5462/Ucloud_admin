@echo off
chcp 65001 >nul
echo ========================================
echo 云电脑容器管理系统 - 一键启动脚本
echo ========================================
echo.

REM 启动后端服务
echo [1/3] 正在启动后端服务...
start "后端服务" cmd /k "cd /d %~dp0backend && python run.py"

timeout /t 3 /nobreak >nul

REM 启动前端服务
echo [2/3] 正在启动后台管理前端...
start "后台管理" cmd /k "cd /d %~dp0admin-frontend && npm run dev"

timeout /t 3 /nobreak >nul

REM 显示客户端启动方式
echo [3/3] 客户端启动方式:
echo     cd client ^&^& python main.py
echo.
echo ========================================
echo 服务启动完成！
echo ========================================
echo.
echo 访问地址:
echo   后端API:   http://localhost:8000
echo   API文档:   http://localhost:8000/docs
echo   后台管理:  http://localhost:5173
echo.
echo 默认管理员账号:
echo   用户名: admin
echo   密码: Admin123@
echo.
echo ========================================

pause
