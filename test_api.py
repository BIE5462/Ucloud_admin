import requests
import json

BASE_URL = "http://localhost:8000"


def test_health():
    """测试服务健康状态"""
    print("=" * 50)
    print("测试1: 检查服务健康状态")
    print("=" * 50)
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"状态码: {resp.status_code}")
        print(f"响应: {resp.text}")
        return resp.status_code == 200
    except Exception as e:
        print(f"[错误] {e}")
        print("提示: 后端服务可能未启动，请先运行: python backend/run.py")
        return False


def test_admin_login():
    """测试管理员登录"""
    print("\n" + "=" * 50)
    print("测试2: 管理员登录")
    print("=" * 50)
    print(f"请求URL: {BASE_URL}/api/auth/admin/login")
    print(f"请求数据: {{'username': 'admin', 'password': 'Admin123@'}}")

    try:
        resp = requests.post(
            f"{BASE_URL}/api/auth/admin/login",
            json={"username": "admin", "password": "Admin123@"},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        print(f"\n状态码: {resp.status_code}")
        data = resp.json()
        print(f"响应码: {data.get('code')}")
        print(f"消息: {data.get('message')}")

        if data.get("code") == 200:
            print(f"✅ 登录成功!")
            print(f"Token: {data.get('data', {}).get('token', 'N/A')}")
            print(f"管理员: {data.get('data', {}).get('admin', {})}")
            return True
        else:
            print(f"[失败] 登录失败: {data.get('message')}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败: 无法连接到 {BASE_URL}")
        print("   请确保后端服务已启动: python backend/run.py")
        return False
    except Exception as e:
        print(f"[错误] {e}")
        return False


def test_user_login():
    """测试用户登录"""
    print("\n" + "=" * 50)
    print("测试3: 用户登录")
    print("=" * 50)
    print(f"请求URL: {BASE_URL}/api/auth/login")
    print(f"请求数据: {{'phone': '13800138000', 'password': '13800138000'}}")

    try:
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"phone": "13800138000", "password": "123456"},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        print(f"\n状态码: {resp.status_code}")
        data = resp.json()
        print(f"响应码: {data.get('code')}")
        print(f"消息: {data.get('message')}")

        if data.get("code") == 200:
            print(f"✅ 登录成功!")
            return True
        else:
            print(f"[失败] 登录失败: {data.get('message')}")
            print("   (这是正常的，因为还没有创建用户)")
            return False

    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败: 无法连接到 {BASE_URL}")
        return False
    except Exception as e:
        print(f"[错误] {e}")
        return False


def main():
    print("\n云电脑管理系统 - API测试工具")
    print("=" * 50)

    # 检查后端是否运行
    if not test_health():
        print("\n[警告] 后端服务未启动，请先运行:")
        print("   cd backend && python run.py")
        return

    # 测试管理员登录
    test_admin_login()

    # 测试用户登录
    test_user_login()

    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)


if __name__ == "__main__":
    main()
