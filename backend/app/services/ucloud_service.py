import base64
from ucloud.core import exc
from ucloud.client import Client
from app.core.config import get_settings

settings = get_settings()


class UCloudService:
    """UCloud服务封装"""

    def __init__(self):
        self.client = Client(
            {
                "region": settings.UCLOUD_REGION,
                "public_key": settings.UCLOUD_PUBLIC_KEY,
                "private_key": settings.UCLOUD_PRIVATE_KEY,
                "base_url": settings.UCLOUD_BASE_URL,
            }
        )

    async def create_container(
        self,
        instance_name: str,
        gpu_type: str = "3090",
        cpu_cores: int = 12,
        memory_gb: int = 32,
        storage_gb: int = 200,
    ) -> dict:
        """创建容器实例"""
        try:
            # 创建容器实例
            create_resp = self.client.ucompshare().create_comp_share_instance(
                {
                    "Zone": settings.UCLOUD_ZONE,
                    "MachineType": "G",
                    "CompShareImageId": settings.UCLOUD_IMAGE_ID,
                    "GPU": 1,
                    "GpuType": gpu_type,
                    "CPU": cpu_cores,
                    "Memory": memory_gb * 1024,  # 转换为MB
                    "ChargeType": "Postpay",
                    "Disks": [
                        {"IsBoot": True, "Size": storage_gb, "Type": "CLOUD_SSD"}
                    ],
                    "Name": instance_name,
                }
            )

            # 获取新创建的实例ID
            instance_ids = create_resp.get("UHostIds")

            if not instance_ids:
                return {"success": False, "error": "创建失败，未返回实例ID"}

            # 查询实例详情
            describe_resp = self.client.ucompshare().describe_comp_share_instance(
                {
                    "UHostIds": instance_ids,
                }
            )

            data = describe_resp["UHostSet"][0]

            return {
                "success": True,
                "instance_id": data["UHostId"],
                "ip": data["IPSet"][1]["IP"]
                if len(data["IPSet"]) > 1
                else data["IPSet"][0]["IP"],
                "password": base64.b64decode(data["Password"]).decode(),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def start_container(self, instance_id: str) -> dict:
        """启动容器实例"""
        try:
            start_resp = self.client.ucompshare().start_comp_share_instance(
                {
                    "Region": settings.UCLOUD_REGION,
                    "Zone": settings.UCLOUD_ZONE,
                    "UHostId": instance_id,
                }
            )

            if start_resp:
                # 获取最新的连接信息
                describe_resp = self.client.ucompshare().describe_comp_share_instance(
                    {
                        "UHostIds": [instance_id],
                    }
                )

                data = describe_resp["UHostSet"][0]

                return {
                    "success": True,
                    "ip": data["IPSet"][1]["IP"]
                    if len(data["IPSet"]) > 1
                    else data["IPSet"][0]["IP"],
                    "password": base64.b64decode(data["Password"]).decode(),
                }
            else:
                return {"success": False, "error": "启动失败"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def stop_container(self, instance_id: str) -> dict:
        """停止容器实例"""
        try:
            stop_resp = self.client.ucompshare().stop_comp_share_instance(
                {
                    "Region": settings.UCLOUD_REGION,
                    "Zone": settings.UCLOUD_ZONE,
                    "UHostId": instance_id,
                }
            )

            if stop_resp:
                return {"success": True}
            else:
                return {"success": False, "error": "停止失败"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete_container(self, instance_id: str) -> dict:
        """删除容器实例"""
        try:
            delete_resp = self.client.ucompshare().terminate_comp_share_instance(
                {
                    "Region": settings.UCLOUD_REGION,
                    "Zone": settings.UCLOUD_ZONE,
                    "UHostId": instance_id,
                }
            )

            if delete_resp:
                return {"success": True}
            else:
                return {"success": False, "error": "删除失败"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_instance_info(self, instance_id: str) -> dict:
        """获取实例信息"""
        try:
            describe_resp = self.client.ucompshare().describe_comp_share_instance(
                {
                    "UHostIds": [instance_id],
                }
            )

            data = describe_resp["UHostSet"][0]

            return {
                "success": True,
                "instance_id": data["UHostId"],
                "status": data["State"],
                "ip": data["IPSet"][1]["IP"]
                if len(data["IPSet"]) > 1
                else data["IPSet"][0]["IP"],
                "password": base64.b64decode(data["Password"]).decode(),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


# 全局UCloud服务实例
ucloud_service = UCloudService()
