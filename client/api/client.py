"""API客户端 - 增强版（支持重试和更好的错误处理）"""

import time
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
import requests

from config import get_config

logger = logging.getLogger(__name__)


class APIError(Exception):
    """API错误基类"""

    def __init__(self, message: str, code: int = None, response: dict = None):
        self.message = message
        self.code = code
        self.response = response
        super().__init__(self.message)


class NetworkError(APIError):
    """网络错误"""

    pass


class AuthenticationError(APIError):
    """认证错误"""

    pass


class ServerError(APIError):
    """服务器错误"""

    pass


def retry_on_error(max_retries: int = None, delay: float = None):
    """
    重试装饰器

    Args:
        max_retries: 最大重试次数
        delay: 重试间隔（秒）
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = get_config()
            retries = max_retries or config.api_max_retries
            wait_time = delay or config.api_retry_delay

            last_error = None
            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.RequestException, NetworkError) as e:
                    last_error = e
                    if attempt < retries:
                        logger.warning(
                            f"请求失败，{wait_time}秒后重试 ({attempt + 1}/{retries}): {e}"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"请求最终失败: {e}")
                        raise NetworkError(f"网络请求失败: {str(e)}")
                except APIError:
                    # API错误不重试
                    raise

            raise last_error

        return wrapper

    return decorator


class APIClient:
    """API客户端 - 增强版"""

    def __init__(self):
        self.token: Optional[str] = None
        self.config = get_config()
        self.session = requests.Session()

    def set_token(self, token: str):
        """设置认证Token"""
        self.token = token

    def clear_token(self):
        """清除认证Token"""
        self.token = None

    def _headers(self) -> Dict[str, str]:
        """构建请求头"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        处理API响应

        Args:
            response: HTTP响应

        Returns:
            解析后的JSON数据

        Raises:
            APIError: API返回错误
            AuthenticationError: 认证失败
            ServerError: 服务器错误
        """
        try:
            data = response.json()
        except Exception as e:
            logger.error(f"解析响应失败: {e}")
            raise APIError(f"无法解析服务器响应: {str(e)}")

        # 检查HTTP状态码
        if response.status_code == 401:
            raise AuthenticationError("认证失败，请重新登录")
        elif response.status_code >= 500:
            raise ServerError(f"服务器错误 (HTTP {response.status_code})")
        elif response.status_code >= 400:
            message = data.get("message", f"请求错误 (HTTP {response.status_code})")
            raise APIError(message, code=response.status_code)

        # 检查业务状态码
        code = data.get("code", 200)
        if code != 200:
            message = data.get("message", f"业务错误 (Code {code})")
            raise APIError(message, code=code, response=data)

        return data

    @retry_on_error()
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        发送HTTP请求

        Args:
            method: HTTP方法
            endpoint: API端点
            **kwargs: 其他请求参数

        Returns:
            响应数据
        """
        url = f"{self.config.api_base_url}{endpoint}"

        # 合并headers
        headers = self._headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=self.config.api_timeout,
                **kwargs,
            )
            return self._handle_response(response)
        except requests.exceptions.Timeout:
            raise NetworkError(f"请求超时 ({self.config.api_timeout}秒)")
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"连接失败: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"请求异常: {str(e)}")

    # ==================== 认证接口 ====================

    def login(self, phone: str, password: str) -> tuple[bool, Any]:
        """
        用户登录

        Returns:
            (成功标志, 结果数据或错误信息)
        """
        try:
            data = self._request(
                "POST", "/auth/login", json={"phone": phone, "password": password}
            )
            self.token = data["data"]["token"]
            return True, data["data"]
        except APIError as e:
            return False, e.message
        except Exception as e:
            logger.error(f"登录异常: {e}")
            return False, str(e)

    # ==================== 云电脑接口 ====================

    def get_my_container(self) -> Dict[str, Any]:
        """获取我的云电脑"""
        try:
            return self._request("GET", "/container/my")
        except APIError as e:
            return {"code": e.code or 500, "message": e.message}
        except Exception as e:
            return {"code": 500, "message": str(e)}

    def get_container_status(self) -> Dict[str, Any]:
        """获取云电脑状态"""
        try:
            return self._request("GET", "/container/my/status")
        except APIError as e:
            return {"code": e.code or 500, "message": e.message}
        except Exception as e:
            return {"code": 500, "message": str(e)}

    def create_container(
        self,
        instance_name: str,
    ) -> Dict[str, Any]:
        """创建云电脑

        使用固定默认参数，仅实例名称可自定义。
        """
        try:
            return self._request(
                "POST",
                "/container",
                json={
                    "instance_name": instance_name,
                },
            )
        except APIError as e:
            return {"code": e.code or 500, "message": e.message}
        except Exception as e:
            return {"code": 500, "message": str(e)}

    def start_container(self) -> Dict[str, Any]:
        """启动云电脑"""
        try:
            return self._request("POST", "/container/start")
        except APIError as e:
            return {"code": e.code or 500, "message": e.message}
        except Exception as e:
            return {"code": 500, "message": str(e)}

    def stop_container(self) -> Dict[str, Any]:
        """停止云电脑"""
        try:
            return self._request("POST", "/container/stop")
        except APIError as e:
            return {"code": e.code or 500, "message": e.message}
        except Exception as e:
            return {"code": 500, "message": str(e)}

    def delete_container(
        self, confirm: bool = True, reason: str = None
    ) -> Dict[str, Any]:
        """删除云电脑"""
        try:
            return self._request(
                "DELETE", "/container", json={"confirm": confirm, "reason": reason}
            )
        except APIError as e:
            return {"code": e.code or 500, "message": e.message}
        except Exception as e:
            return {"code": 500, "message": str(e)}

    def get_container_info(self) -> Dict[str, Any]:
        """获取云电脑详细信息（包含UHostId和密码）"""
        try:
            return self._request("GET", "/container/my/info")
        except APIError as e:
            return {"code": e.code or 500, "message": e.message}
        except Exception as e:
            return {"code": 500, "message": str(e)}

    # ==================== 计费接口 ====================

    def get_billing_statistics(self) -> Dict[str, Any]:
        """获取消费统计"""
        try:
            return self._request("GET", "/billing/statistics")
        except APIError as e:
            return {"code": e.code or 500, "message": e.message}
        except Exception as e:
            return {"code": 500, "message": str(e)}

    def get_billing_history(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """获取消费历史"""
        try:
            return self._request(
                "GET", "/billing/history", params={"page": page, "page_size": page_size}
            )
        except APIError as e:
            return {"code": e.code or 500, "message": e.message}
        except Exception as e:
            return {"code": 500, "message": str(e)}

    def get_current_session(self) -> Dict[str, Any]:
        """获取当前会话计费信息"""
        try:
            return self._request("GET", "/billing/current-session")
        except APIError as e:
            return {"code": e.code or 500, "message": e.message}
        except Exception as e:
            return {"code": 500, "message": str(e)}


# 全局API客户端实例
api_client = APIClient()
