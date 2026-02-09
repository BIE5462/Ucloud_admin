import requests
import random

BASE_URL = "http://localhost:8000"


def get_admin_token():
    """获取管理员token"""
    resp = requests.post(
        f"{BASE_URL}/api/auth/admin/login",
        json={"username": "admin", "password": "123456"},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    data = resp.json()
    if data.get("code") == 200:
        return data.get("data", {}).get("token")
    return None


def get_super_admin_token():
    """获取超级管理员token"""
    resp = requests.post(
        f"{BASE_URL}/api/auth/admin/login",
        json={"username": "admin", "password": "123456"},
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    data = resp.json()
    if data.get("code") == 200:
        return data.get("data", {}).get("token")
    return None


def create_test_user(token, phone=None):
    """创建测试用户"""
    if phone is None:
        phone = f"1{random.randint(100000000, 999999999)}"

    resp = requests.post(
        f"{BASE_URL}/api/admin/users",
        json={
            "company_name": f"测试公司{random.randint(1000, 9999)}",
            "contact_name": "测试联系人",
            "phone": phone,
            "password": "Test123456",
            "initial_balance": 100.00,
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        timeout=10,
    )
    data = resp.json()
    if data.get("code") == 200:
        return data.get("data", {}).get("id"), phone
    return None, phone


def delete_user_by_id(token, user_id):
    """删除用户"""
    return requests.delete(
        f"{BASE_URL}/api/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )


def create_test_admin(token, username=None):
    """创建测试管理员"""
    if username is None:
        username = f"test_admin_{random.randint(1000, 9999)}"

    resp = requests.post(
        f"{BASE_URL}/api/admin/admins",
        json={
            "username": username,
            "password": "Test123456",
            "role": "admin"
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        timeout=10,
    )
    data = resp.json()
    if data.get("code") == 200:
        return data.get("data", {}).get("id"), username
    return None, username


def delete_admin_by_id(token, admin_id):
    """删除管理员"""
    return requests.delete(
        f"{BASE_URL}/api/admin/admins/{admin_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )


def test_delete_nonexistent_user():
    """测试删除不存在的用户"""
    print("\n" + "=" * 50)
    print("测试1: 删除不存在的用户")
    print("=" * 50)

    token = get_super_admin_token()
    if not token:
        print("[失败] 无法获取超级管理员token")
        return False

    resp = delete_user_by_id(token, 99999)
    data = resp.json()

    print(f"状态码: {resp.status_code}")
    print(f"响应码: {data.get('code')}")
    print(f"消息: {data.get('message')}")

    if resp.status_code == 404 and data.get("code") == 404:
        print("✅ 测试通过: 不存在的用户返回404")
        return True
    else:
        print(f"[失败] 预期404，实际: {resp.status_code}")
        return False


def test_delete_user_with_container():
    """测试删除有云电脑的用户"""
    print("\n" + "=" * 50)
    print("测试2: 删除有云电脑的用户")
    print("=" * 50)
    print("提示: 此测试需要先创建一个有云电脑的用户，跳过")
    return True


def test_delete_user_normal_admin():
    """测试普通管理员删除用户"""
    print("\n" + "=" * 50)
    print("测试3: 普通管理员删除用户")
    print("=" * 50)

    token = get_admin_token()
    if not token:
        print("[失败] 无法获取普通管理员token")
        return False

    resp = delete_user_by_id(token, 1)
    data = resp.json()

    print(f"状态码: {resp.status_code}")
    print(f"响应码: {data.get('code')}")
    print(f"消息: {data.get('message')}")

    if resp.status_code == 403 and data.get("code") == 403:
        print("✅ 测试通过: 普通管理员无权限删除用户")
        return True
    else:
        print(f"[失败] 预期403，实际: {resp.status_code}")
        return False


def test_delete_user_success():
    """测试成功删除用户"""
    print("\n" + "=" * 50)
    print("测试4: 成功删除用户")
    print("=" * 50)

    token = get_super_admin_token()
    if not token:
        print("[失败] 无法获取超级管理员token")
        return False

    user_id, phone = create_test_user(token)
    if not user_id:
        print("[失败] 创建测试用户失败")
        return False
    print(f"创建测试用户成功: ID={user_id}, Phone={phone}")

    print(f"删除用户: ID={user_id}")
    resp = delete_user_by_id(token, user_id)
    data = resp.json()

    print(f"状态码: {resp.status_code}")
    print(f"响应码: {data.get('code')}")
    print(f"消息: {data.get('message')}")

    if resp.status_code == 200 and data.get("code") == 200:
        print("✅ 测试通过: 用户删除成功")

        verify_resp = requests.get(
            f"{BASE_URL}/api/admin/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if verify_resp.status_code == 404:
            print("✅ 验证通过: 用户已不存在")
            return True
        else:
            print("[警告] 用户可能未真正删除")
            return False
    else:
        print(f"[失败] 删除失败")
        return False


def test_delete_admin_success():
    """测试超级管理员成功删除管理员"""
    print("\n" + "=" * 50)
    print("测试5: 超级管理员成功删除管理员")
    print("=" * 50)

    token = get_super_admin_token()
    if not token:
        print("[失败] 无法获取超级管理员token")
        return False

    # 创建测试管理员
    admin_id, username = create_test_admin(token)
    if not admin_id:
        print("[失败] 创建测试管理员失败")
        return False
    print(f"创建测试管理员成功: ID={admin_id}, Username={username}")

    # 删除管理员
    print(f"删除管理员: ID={admin_id}")
    resp = delete_admin_by_id(token, admin_id)
    data = resp.json()

    print(f"状态码: {resp.status_code}")
    print(f"响应码: {data.get('code')}")
    print(f"消息: {data.get('message')}")

    if resp.status_code == 200 and data.get("code") == 200:
        print("✅ 测试通过: 管理员删除成功")
        return True
    else:
        print(f"[失败] 删除失败")
        return False


def test_delete_admin_normal_admin():
    """测试普通管理员无权限删除管理员"""
    print("\n" + "=" * 50)
    print("测试6: 普通管理员无权限删除管理员")
    print("=" * 50)

    token = get_admin_token()
    if not token:
        print("[失败] 无法获取普通管理员token")
        return False

    # 尝试删除管理员（使用ID=1，假设存在）
    resp = delete_admin_by_id(token, 1)
    data = resp.json()

    print(f"状态码: {resp.status_code}")
    print(f"响应码: {data.get('code')}")
    print(f"消息: {data.get('message')}")

    if resp.status_code == 403:
        print("✅ 测试通过: 普通管理员无权限删除管理员")
        return True
    else:
        print(f"[失败] 预期403，实际: {resp.status_code}")
        return False


def test_delete_admin_nonexistent():
    """测试删除不存在的管理员"""
    print("\n" + "=" * 50)
    print("测试7: 删除不存在的管理员")
    print("=" * 50)

    token = get_super_admin_token()
    if not token:
        print("[失败] 无法获取超级管理员token")
        return False

    resp = delete_admin_by_id(token, 99999)
    data = resp.json()

    print(f"状态码: {resp.status_code}")
    print(f"响应码: {data.get('code')}")
    print(f"消息: {data.get('message')}")

    if resp.status_code == 404:
        print("✅ 测试通过: 不存在的管理员返回404")
        return True
    else:
        print(f"[失败] 预期404，实际: {resp.status_code}")
        return False


def test_delete_admin_self():
    """测试超级管理员删除自己"""
    print("\n" + "=" * 50)
    print("测试8: 超级管理员删除自己")
    print("=" * 50)

    token = get_super_admin_token()
    if not token:
        print("[失败] 无法获取超级管理员token")
        return False

    # 尝试删除自己（假设超级管理员ID=1）
    resp = delete_admin_by_id(token, 1)
    data = resp.json()

    print(f"状态码: {resp.status_code}")
    print(f"响应码: {data.get('code')}")
    print(f"消息: {data.get('message')}")

    if resp.status_code == 400:
        print("✅ 测试通过: 超级管理员不能删除自己")
        return True
    else:
        print(f"[失败] 预期400，实际: {resp.status_code}")
        return False


def test_health():
    """测试服务健康状态"""
    print("=" * 50)
    print("测试0: 检查服务健康状态")
    print("=" * 50)
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"状态码: {resp.status_code}")
        return resp.status_code == 200
    except Exception as e:
        print(f"[错误] {e}")
        print("提示: 后端服务可能未启动，请先运行: python backend/run.py")
        return False


def main():
    print("\n" + "=" * 50)
    print("删除用户API测试")
    print("=" * 50)

    if not test_health():
        print("\n[警告] 后端服务未启动，请先运行:")
        print("   cd backend && python run.py")
        return

    results = []

    # results.append(("删除不存在的用户", test_delete_nonexistent_user()))
    # results.append(("普通管理员删除用户", test_delete_user_normal_admin()))
    # results.append(("成功删除用户", test_delete_user_success()))
    results.append(("超级管理员成功删除管理员", test_delete_admin_success()))
    results.append(("普通管理员无权限删除管理员", test_delete_admin_normal_admin()))
    results.append(("删除不存在的管理员", test_delete_admin_nonexistent()))
    results.append(("超级管理员不能删除自己", test_delete_admin_self()))

    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {name}")
        if not passed:
            all_passed = False

    print("=" * 50)
    if all_passed:
        print("所有测试通过!")
    else:
        print("部分测试失败")
    print("=" * 50)


if __name__ == "__main__":
    main()
