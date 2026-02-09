"""
容器实例创建 API 测试脚本
测试 /api/container 端点的容器创建功能
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"


def test_health():
    """测试服务健康状态"""
    print("=" * 60)
    print("步骤 1: 检查服务健康状态")
    print("=" * 60)
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✅ 服务状态: {resp.status_code}")
        print(f"响应: {resp.text}")
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ [错误] {e}")
        print("提示: 后端服务可能未启动，请先运行: python backend/run.py")
        return False


def user_login(phone="12345678900", password="123456"):
    """用户登录，获取 Token"""
    print("\n" + "=" * 60)
    print("步骤 2: 用户登录获取 Token")
    print("=" * 60)
    print(f"请求: POST {BASE_URL}/api/auth/login")
    print(f"参数: phone={phone}, password={password}")

    try:
        resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"phone": phone, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        data = resp.json()
        print(f"\n状态码: {resp.status_code}")
        print(f"响应码: {data.get('code')}")
        print(f"消息: {data.get('message')}")

        if data.get("code") == 200:
            token = data.get("data", {}).get("token")
            user_info = data.get("data", {}).get("user", {})
            print(f"✅ 登录成功!")
            print(f"用户ID: {user_info.get('id')}")
            print(f"用户名: {user_info.get('company_name')}")
            print(f"余额: {user_info.get('balance')} 元")
            return token
        else:
            print(f"❌ 登录失败: {data.get('message')}")
            return None

    except Exception as e:
        print(f"❌ [错误] {e}")
        return None


def create_container(token, instance_name="测试实例"):
    """测试创建容器实例"""
    print("\n" + "=" * 60)
    print("步骤 3: 创建容器实例")
    print("=" * 60)
    print(f"请求: POST {BASE_URL}/api/container")
    print(f"请求头: Authorization: Bearer {token[:20]}...")
    print(f"请求体: {{'instance_name': '{instance_name}'}}")

    try:
        resp = requests.post(
            f"{BASE_URL}/api/container",
            json={"instance_name": instance_name},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            timeout=15,
        )

        data = resp.json()
        print(f"\n状态码: {resp.status_code}")
        print(f"响应码: {data.get('code')}")
        print(f"消息: {data.get('message')}")

        if resp.status_code == 200 and data.get("code") == 200:
            container_data = data.get("data", {})
            print(f"✅ 容器创建成功!")
            print(f"容器ID: {container_data.get('container_id')}")
            print(f"状态: {container_data.get('status')}")
            print(f"预计创建时间: {container_data.get('estimated_time')} 秒")
            return container_data.get("container_id")
        elif resp.status_code == 400:
            print(f"⚠️ 请求错误: {data.get('detail', data.get('message'))}")
            print("   可能原因: 用户已有容器实例")
        elif resp.status_code == 402:
            print(f"⚠️ 余额不足: {data.get('detail', data.get('message'))}")
        elif resp.status_code == 500:
            print(f"❌ 服务器错误: {data.get('detail', data.get('message'))}")
        else:
            print(f"❌ 创建失败: {data.get('detail', data.get('message'))}")

        return None

    except requests.exceptions.ConnectionError:
        print(f"❌ 连接失败: 无法连接到 {BASE_URL}")
        return None
    except Exception as e:
        print(f"❌ [错误] {e}")
        return None


def get_my_container(token):
    """获取我的容器信息"""
    print("\n" + "=" * 60)
    print("步骤 4: 获取我的容器信息")
    print("=" * 60)
    print(f"请求: GET {BASE_URL}/api/container/my")

    try:
        resp = requests.get(
            f"{BASE_URL}/api/container/my",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )

        data = resp.json()
        print(f"\n状态码: {resp.status_code}")
        print(f"响应码: {data.get('code')}")

        if resp.status_code == 200:
            container_data = data.get("data", {})
            if container_data.get("has_container"):
                container = container_data.get("container", {})
                print(f"✅ 找到容器实例!")
                print(f"  容器ID: {container.get('id')}")
                print(f"  实例名称: {container.get('instance_name')}")
                print(f"  状态: {container.get('status')}")
                print(f"  GPU类型: {container.get('gpu_type')}")
                print(f"  CPU核心: {container.get('cpu_cores')}")
                print(f"  内存: {container.get('memory_gb')} GB")
                print(f"  存储: {container.get('storage_gb')} GB")
                print(f"  单价: {container.get('price_per_minute')} 元/分钟")
                print(f"  运行时长: {container.get('total_running_minutes')} 分钟")
                print(f"  总费用: {container.get('total_cost')} 元")
            else:
                print("ℹ️ 用户暂无容器实例")
        else:
            print(f"❌ 获取失败: {data.get('message')}")

    except Exception as e:
        print(f"❌ [错误] {e}")


def main():
    print("\n" + "=" * 60)
    print("容器实例创建 API 测试")
    print("=" * 60)

    # 检查服务健康状态
    if not test_health():
        print("\n❌ 后端服务未启动，测试终止")
        print("请先运行: cd backend && python run.py")
        sys.exit(1)

    # 用户登录获取 Token
    token = user_login()
    if not token:
        print("\n❌ 登录失败，测试终止")
        sys.exit(1)

    # 创建容器实例
    container_id = create_container(token, instance_name="API测试实例")

    # 获取容器信息
    get_my_container(token)

    # 测试总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    if container_id:
        print(f"✅ 容器创建成功 (ID: {container_id})")
    else:
        print("⚠️ 容器创建失败或用户已有容器")
    print("=" * 60)


if __name__ == "__main__":
    main()
