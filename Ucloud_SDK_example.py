from ucloud.core import exc
from ucloud.client import Client
import base64
client = Client({
    "region": "cn-wlcb",  # 总是cn-wlcb
    "public_key": "4eZCt9GH5fS1XEutXeyTtv6A0QReFzqW5",  # 公钥私钥从https://console.compshare.cn/uaccount/api_manage获取
    "private_key": "9W5iDOdYn7cJxUaEgsYhMVCvhYR71fraGHpkmmJjuWmU",
    "base_url": "https://api.compshare.cn"  # 总是https://api.compshare.cn
})

import base64
#指定用户创建实例
def create_container(uid):
    global client
    try:
        # 创建容器实例
        create_resp = client.ucompshare().create_comp_share_instance({
            "Zone": "cn-wlcb-01",  # 总是cn-wlcb-01
            "MachineType": "G",  # 总是G
            "CompShareImageId": "compshareImage-1mnqn08rd1xz",  # 使用的镜像ID
            "GPU": 1,  # GPU数量
            "GpuType": "3080Ti",  # GPU类型，可以是4090、3080Ti或3090                                                                                     
            "CPU": 12,  # CPU核心数
            "Memory": 32768,  # 内存大小，64*1024表示64G
            "ChargeType": "Postpay",
            "Disks": [
                {
                    "IsBoot": True,
                    "Size": 200,  # 系统盘大小，200表示200G
                    "Type": "CLOUD_SSD"
                }
            ],
            "Name": "测试实例"
        })
        
        # 获取新创建的实例ID
        instance_ids = create_resp.get("UHostIds")
        
        # 查询实例详情
        describe_resp = client.ucompshare().describe_comp_share_instance({
            "UHostIds": instance_ids,
        })
        
        # 提取实例数据
        data = describe_resp['UHostSet'][0]
        print(f"创建实例成功，实例ID: {data['UHostId']}，IP: {data['IPSet'][1]['IP']}，密码: {base64.b64decode(data['Password']).decode()}")
        
        return data['UHostId']

    except Exception as e:
        print(e)
        return 'error,' + str(e)


def create_container(uid):
    global client
    try:
        # 创建容器实例
        create_resp = client.ucompshare().create_comp_share_instance({
            "Zone": "cn-wlcb-01",  # 总是cn-wlcb-01
            "MachineType": "G",  # 总是G
            "CompShareImageId": "compshareImage-1mnqn08rd1xz",  # 使用的镜像ID
            "GPU": 1,  # GPU数量
            "GpuType": "3080Ti",  # GPU类型，可以是4090、3080Ti或3090
            "CPU": 12,  # CPU核心数
            "Memory": 32768,  # 内存大小，64*1024表示64G
            "ChargeType": "Postpay",
            "Disks": [
                {
                    "IsBoot": True,
                    "Size": 200,  # 系统盘大小，200表示200G
                    "Type": "CLOUD_SSD"
                }
            ],
            "Name": "测试"
        })
        
        # 获取新创建的实例ID
        instance_ids = create_resp.get("UHostIds")
        
        # 查询实例详情
        describe_resp = client.ucompshare().describe_comp_share_instance({
            "UHostIds": instance_ids,
        })
        
        # 提取实例数据
        data = describe_resp['UHostSet'][0]
        print(f"创建实例成功，实例ID: {data['UHostId']}，IP: {data['IPSet'][1]['IP']}，密码: {base64.b64decode(data['Password']).decode()}")
        
        return data['UHostId']

    except Exception as e:
        print(e)
        return 'error,' + str(e)

#启动已有实例
def start_container(UHostId):
    global client

    # 启动容器实例
    start_resp = client.ucompshare().start_comp_share_instance({
        "Region": "cn-wlcb",
        "Zone": "cn-wlcb-01",
        "UHostId": UHostId
    })
    
    if bool(start_resp) == True:
        return '容器启动成功！'
    else:
        return '开机失败！请检查容器实例状态！'


# 停止实例
def stop_container(UHostId):
    global client


    # 停止容器实例
    stop_resp = client.ucompshare().stop_comp_share_instance({
        "Region": "cn-wlcb",
        "Zone": "cn-wlcb-01",
        "UHostId": UHostId
    })
    if bool(stop_resp) == True:
        return '容器关闭成功！'
    else:
        return '关机失败！可能不存在该实例！'

#删除容器实例
def delete_container(UHostId):
    global client
    # 删除容器实例
    delete_resp = client.ucompshare().terminate_comp_share_instance({
        "Region": "cn-wlcb",
        "Zone": "cn-wlcb-01",
        "UHostId": UHostId
    })
    print("这里在关机!")
    if bool(delete_resp) == True:
        # 清空容器记录
        return '实例删除成功！'
    else:
        return '删除失败！可能该实例已删除，请联系管理员！'

# 根据实例ID获取实例数据并打印
def get_instance_data(instance_id):
    global client
    try:
        # 查询实例详情
        describe_resp = client.ucompshare().describe_comp_share_instance({
            "UHostIds": [instance_id],
        })
        
        # 提取实例数据
        data = describe_resp['UHostSet'][0]
        print(f"实例ID: {data['UHostId']}，IP: {data['IPSet'][1]['IP']}，密码: {base64.b64decode(data['Password']).decode()}")
        
    except Exception as e:
        print(e)
        return 'error,' + str(e)


if __name__ == "__main__":
    print("=== Ucloud 容器管理调用案例 ===")
    
    # 案例1: 创建容器实例
    print("\n1. 创建容器实例:")
    user_id = "user123"
    instance_id = create_container(user_id)
    print(f"实例id: {instance_id}")
    
    # 案例2: 启动已有实例
    print("\n2. 启动已有实例:")
    instance_id = "uhost-1mnsltm8nutn"
    start_result = start_container(instance_id)
    print(f"启动结果: {start_result}")
    
    # 案例5: 获取实例数据
    print("\n5. 获取实例数据:")
    get_instance_data(instance_id)

    # 案例3: 停止实例
    print("\n3. 停止实例:")
    stop_result = stop_container(instance_id)
    print(f"停止结果: {stop_result}")
    
    # 案例4: 删除容器实例
    print("\n4. 删除容器实例:")
    delete_result = delete_container(instance_id)
    print(f"删除结果: {delete_result}")
    





