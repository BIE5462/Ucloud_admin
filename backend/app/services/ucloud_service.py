import base64
from ucloud.client import Client
from app.core.config import get_settings

settings = get_settings()


class UCloudService:
    """UCloud服务封装"""

    @staticmethod
    def build_client(server):
        """根据服务器配置构建 UCloud 客户端"""
        return Client(
            {
                "region": settings.UCLOUD_REGION,
                "public_key": server.ucloud_public_key,
                "private_key": server.ucloud_private_key,
                "base_url": settings.UCLOUD_BASE_URL,
            }
        )

    async def create_container(
        self,
        server,
        instance_name: str,
        create_config: dict,
    ) -> dict:
        """创建容器实例

        创建参数从系统后台配置读取，仅部分底层参数保持固定。
        参考 Ucloud_SDK_example.py 中的创建方式。
        """
        try:
            client = self.build_client(server)
            # 创建容器实例 - 核心规格来自系统配置
            create_payload = self.build_create_payload(
                server=server,
                instance_name=instance_name,
                create_config=create_config,
            )
            create_resp = client.ucompshare().create_comp_share_instance(create_payload)

            # 获取新创建的实例ID
            instance_ids = create_resp.get("UHostIds")

            if not instance_ids:
                return {"success": False, "error": "创建失败，未返回实例ID"}

            # 查询实例详情
            describe_resp = client.ucompshare().describe_comp_share_instance(
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

    @staticmethod
    def build_create_payload(server, instance_name: str, create_config: dict) -> dict:
        """构建创建容器实例的请求参数"""
        return {
            "Zone": "cn-wlcb-01",
            "MachineType": "G",
            "CompShareImageId": server.ucloud_image_id,
            "GPU": 1,
            "GpuType": create_config["gpu_type"],
            "CPU": create_config["cpu_cores"],
            "Memory": create_config["memory_gb"] * 1024,
            "ChargeType": "Postpay",
            "Disks": [
                {
                    "IsBoot": True,
                    "Size": create_config.get("storage_gb", 200),
                    "Type": "CLOUD_SSD",
                }
            ],
            "Name": instance_name,
        }

    async def start_container(self, server, instance_id: str) -> dict:
        """启动容器实例"""
        try:
            client = self.build_client(server)
            start_resp = client.ucompshare().start_comp_share_instance(
                {
                    "Region": settings.UCLOUD_REGION,
                    "Zone": settings.UCLOUD_ZONE,
                    "UHostId": instance_id,
                }
            )

            if start_resp:
                # 获取最新的连接信息
                describe_resp = client.ucompshare().describe_comp_share_instance(
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

    async def stop_container(self, server, instance_id: str) -> dict:
        """停止容器实例"""
        try:
            client = self.build_client(server)
            stop_resp = client.ucompshare().stop_comp_share_instance(
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

    async def delete_container(self, server, instance_id: str) -> dict:
        """删除容器实例"""
        try:
            client = self.build_client(server)
            delete_resp = client.ucompshare().terminate_comp_share_instance(
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
            error_message = str(e)
            lowered_message = error_message.lower()
            if "not found" in lowered_message or "不存在" in error_message:
                return {"success": True, "already_deleted": True}
            return {"success": False, "error": str(e)}

    async def get_instance_info(self, server, instance_id: str) -> dict:
        """获取实例信息"""
        try:
            client = self.build_client(server)
            describe_resp = client.ucompshare().describe_comp_share_instance(
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
