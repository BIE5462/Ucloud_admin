# 云电脑客户端 - 使用说明

## 📋 功能特性

### 核心功能
- ✅ **一键登录** - 手机号+密码登录
- ✅ **云电脑管理** - 创建、启动、停止、删除
- ✅ **一键RDP连接** - Windows系统自动连接远程桌面
- ✅ **实时计费** - 显示当前消费和剩余时间
- ✅ **账单统计** - 查看今日/本月/累计消费

### 新增功能
- 🆕 **自动RDP连接** - Windows系统自动启动mstsc并填写凭据
- 🆕 **配置管理** - 支持环境变量和配置文件
- 🆕 **自动重试** - API调用失败自动重试
- 🆕 **日志系统** - 支持文件和控制台日志
- 🆕 **跨平台支持** - 非Windows系统显示连接说明

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd client
pip install -r requirements.txt
```

### 2. 启动客户端

```bash
python main.py
```

### 3. 登录

- 输入手机号和密码
- 默认测试账号请联系管理员创建

---

## ⚙️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `API_BASE_URL` | API基础地址 | `http://localhost:8000/api` |
| `API_TIMEOUT` | 请求超时(秒) | `30` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `RDP_AUTO_CONNECT` | 是否自动点击连接 | `true` |

### 配置文件

配置文件位置：
- **Windows**: `%APPDATA%\CloudPCClient\config.json`
- **macOS/Linux**: `~/.config/cloudpc-client/config.json`

示例配置：
```json
{
  "api": {
    "base_url": "http://localhost:8000/api",
    "timeout": 30,
    "max_retries": 3
  },
  "rdp": {
    "auto_connect": true,
    "default_port": 3389,
    "username": "administrator"
  },
  "ui": {
    "window_width": 1000,
    "window_height": 700
  },
  "log": {
    "level": "INFO",
    "to_file": true
  }
}
```

---

## 🖥️ 远程桌面连接

### Windows系统

点击"🖥️ 连接远程桌面"按钮，系统将自动：

1. ✅ 保存凭据到Windows凭据管理器
2. ✅ 启动远程桌面客户端(mstsc)
3. ✅ 自动点击连接按钮
4. ✅ 直接进入桌面

### macOS系统

客户端会显示连接说明：

```
请在macOS上使用以下方式连接:

1. 使用Microsoft Remote Desktop应用:
   - 从App Store下载 Microsoft Remote Desktop
   - 添加PC，输入: <主机地址>
   - 用户名: administrator
   - 密码: <密码>

2. 或使用命令行:
   open "rdp://administrator@<主机地址>"
```

### Linux系统

客户端会显示连接说明：

```
请在Linux上使用以下方式连接:

1. 使用Remmina:
   xfreerdp3 /v:<主机> /u:administrator /p:'<密码>'

2. 使用rdesktop:
   rdesktop -u administrator -p '<密码>' <主机>
```

---

## 📁 项目结构

```
client/
├── main.py                   # 主程序入口
├── config.py                 # 配置管理
├── requirements.txt          # 依赖列表
├── api/
│   ├── __init__.py
│   └── client.py            # API客户端（增强版）
├── utils/
│   ├── __init__.py
│   └── rdp_helper.py        # 远程桌面连接工具
└── logs/                     # 日志目录
```

---

## 🔧 常见问题

### Q: 远程桌面连接失败？

A: 请检查：
1. 是否为Windows系统（仅Windows支持自动连接）
2. 云电脑是否已启动
3. 防火墙是否允许RDP连接
4. 密码是否正确

### Q: 如何修改API地址？

A: 三种方法：
1. 设置环境变量：`set API_BASE_URL=http://your-api.com/api`
2. 修改配置文件
3. 修改 `client/config.py` 中的默认值

### Q: 日志文件在哪里？

A: 
- **Windows**: `%APPDATA%\CloudPCClient\logs\client.log`
- **macOS/Linux**: `~/.config/cloudpc-client/logs/client.log`

### Q: 如何关闭自动连接功能？

A: 设置环境变量：`set RDP_AUTO_CONNECT=false`，
或在配置文件中设置 `"auto_connect": false`

---

## 📞 技术支持

如有问题请联系管理员。

---

## 📝 更新日志

### v1.1.0 (2024-02-09)
- ✨ 新增一键RDP连接功能
- ✨ 新增配置管理系统
- ✨ 新增API自动重试机制
- ✨ 新增日志系统
- ✨ 支持跨平台连接说明
- ♻️ 重构代码结构
- 🎨 优化UI界面

### v1.0.0 (2024-02-08)
- 🎉 首次发布
- 基础云电脑管理功能
- 用户登录认证
- 实时计费显示
