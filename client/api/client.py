"""API客户端 - 增强版（支持重试和更好的错误处理）"""

import time
import logging
import traceback
from typing import Optional, Dict, Any, Callable
from functools import wraps
from dataclasses import dataclass, field
import requests

from config import get_config

logger = logging.getLogger(__name__)


@dataclass
class APIResult:
    """统一的API返回结果"""

    success: bool
    data: Any = None
    message: str = ""
    code: int = 200
    request_id: str = ""
    error_type: str = ""
    error_detail: Dict[str, Any] = field(default_factory=dict)
    traceback_info: str = ""

    def is_ok(self) -> bool:
        """检查是否成功"""
        return self.success and self.code == 200

    def get_error_display(self) -> str:
        """获取错误显示文本"""
        if self.success:
            return ""

        parts = [f"错误: {self.message}"]

        if self.error_type:
            parts.append(f"类型: {self.error_type}")

        if self.request_id:
            parts.append(f"请求ID: {self.request_id}")

        if self.error_detail:
            if self.error_detail.get("error_class"):
                parts.append(f"异常类: {self.error_detail['error_class']}")
            if self.error_detail.get("error_message"):
                parts.append(f"异常信息: {self.error_detail['error_message']}")

        if self.traceback_info:
            parts.append(f"\n堆栈跟踪:\n{self.traceback_info}")

        return "\n".join(parts)


class APIError(Exception):
    """API错误基类"""

    def __init__(
        self,
        message: str,
        code: int = 0,
        response: Optional[dict] = None,
        request_id: str = "",
        error_type: str = "",
    ):
        self.message = message
        self.code = code
        self.response = response if response is not None else {}
        self.request_id = request_id
        self.error_type = error_type
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


def retry_on_error(max_retries: int = 0, delay: float = 0.0):
    """
    重试装饰器

    Args:
        max_retries: 最大重试次数，0表示使用配置
        delay: 重试间隔（秒），0表示使用配置
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = get_config()
            retries = max_retries if max_retries > 0 else config.api_max_retries
            wait_time = delay if delay > 0 else config.api_retry_delay

            last_error: Exception = Exception("未知错误")
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
            raise APIError(
                f"无法解析服务器响应: {str(e)}", code=500, error_type="parse_error"
            )

        # 获取详细错误信息
        request_id = data.get("request_id", "")
        error_type = data.get("error_type", "")
        detail = data.get("detail", {})

        # 检查HTTP状态码
        if response.status_code == 401:
            raise AuthenticationError(
                "认证失败，请重新登录",
                code=401,
                request_id=request_id,
                error_type=error_type or "authentication_error",
            )
        elif response.status_code >= 500:
            raise ServerError(
                data.get("message", f"服务器错误 (HTTP {response.status_code})"),
                code=response.status_code,
                request_id=request_id,
                error_type=error_type or "server_error",
                response=detail,
            )
        elif response.status_code >= 400:
            message = data.get("message", f"请求错误 (HTTP {response.status_code})")
            raise APIError(
                message,
                code=response.status_code,
                request_id=request_id,
                error_type=error_type or "http_error",
                response=detail,
            )

        # 检查业务状态码
        code = data.get("code", 200)
        if code != 200:
            message = data.get("message", f"业务错误 (Code {code})")
            raise APIError(
                message,
                code=code,
                request_id=request_id,
                error_type=error_type or "business_error",
                response=data,
            )

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

    def _make_api_result(
        self,
        success: bool,
        data: Any = None,
        message: str = "",
        code: int = 200,
        request_id: str = "",
        error_type: str = "",
        error_detail: Optional[dict] = None,
        exception: Optional[Exception] = None,
    ) -> APIResult:
        """创建统一的API结果对象"""
        traceback_info = ""
        if exception and not success:
            traceback_info = traceback.format_exc()

        return APIResult(
            success=success,
            data=data,
            message=message,
            code=code,
            request_id=request_id,
            error_type=error_type,
            error_detail=error_detail if error_detail is not None else {},
            traceback_info=traceback_info,
        )

    # ==================== 认证接口 ====================

    def login(self, phone: str, password: str) -> APIResult:
        """
        用户登录

        Returns:
            APIResult: 包含success、data、message等字段的统一结果
        """
        try:
            data = self._request(
                "POST", "/auth/login", json={"phone": phone, "password": password}
            )
            self.token = data["data"]["token"]
            return self._make_api_result(
                success=True, data=data["data"], message="登录成功"
            )
        except APIError as e:
            return self._make_api_result(
                success=False,
                message=e.message,
                code=e.code,
                request_id=e.request_id,
                error_type=e.error_type,
                error_detail=e.response,
                exception=e,
            )
        except Exception as e:
            logger.error(f"登录异常: {e}")
            return self._make_api_result(
                success=False,
                message=f"登录异常: {str(e)}",
                code=500,
                error_type="exception",
                exception=e,
            )

    # ==================== 云电脑接口 ====================

    def get_my_container(self) -> APIResult:
        """获取我的云电脑"""
        try:
            data = self._request("GET", "/container/my")
            return self._make_api_result(
                success=True, data=data.get("data"), message="获取成功"
            )
        except APIError as e:
            return self._make_api_result(
                success=False,
                message=e.message,
                code=e.code,
                request_id=e.request_id,
                error_type=e.error_type,
                error_detail=e.response,
                exception=e,
            )
        except Exception as e:
            return self._make_api_result(
                success=False,
                message=f"获取失败: {str(e)}",
                code=500,
                error_type="exception",
                exception=e,
            )

    def get_container_status(self) -> APIResult:
        """获取云电脑状态"""
        try:
            data = self._request("GET", "/container/my/status")
            return self._make_api_result(
                success=True, data=data.get("data"), message="获取成功"
            )
        except APIError as e:
            return self._make_api_result(
                success=False,
                message=e.message,
                code=e.code,
                request_id=e.request_id,
                error_type=e.error_type,
                error_detail=e.response,
                exception=e,
            )
        except Exception as e:
            return self._make_api_result(
                success=False,
                message=f"获取失败: {str(e)}",
                code=500,
                error_type="exception",
                exception=e,
            )

    def create_container(self, instance_name: str) -> APIResult:
        """创建云电脑"""
        try:
            data = self._request(
                "POST", "/container", json={"instance_name": instance_name}
            )
            return self._make_api_result(
                success=True, data=data.get("data"), message="创建成功"
            )
        except APIError as e:
            return self._make_api_result(
                success=False,
                message=e.message,
                code=e.code,
                request_id=e.request_id,
                error_type=e.error_type,
                error_detail=e.response,
                exception=e,
            )
        except Exception as e:
            return self._make_api_result(
                success=False,
                message=f"创建失败: {str(e)}",
                code=500,
                error_type="exception",
                exception=e,
            )

    def start_container(self) -> APIResult:
        """启动云电脑"""
        try:
            data = self._request("POST", "/container/start")
            return self._make_api_result(
                success=True, data=data.get("data"), message="启动成功"
            )
        except APIError as e:
            return self._make_api_result(
                success=False,
                message=e.message,
                code=e.code,
                request_id=e.request_id,
                error_type=e.error_type,
                error_detail=e.response,
                exception=e,
            )
        except Exception as e:
            return self._make_api_result(
                success=False,
                message=f"启动失败: {str(e)}",
                code=500,
                error_type="exception",
                exception=e,
            )

    def stop_container(self) -> APIResult:
        """停止云电脑"""
        try:
            data = self._request("POST", "/container/stop")
            return self._make_api_result(
                success=True, data=data.get("data"), message="停止成功"
            )
        except APIError as e:
            return self._make_api_result(
                success=False,
                message=e.message,
                code=e.code,
                request_id=e.request_id,
                error_type=e.error_type,
                error_detail=e.response,
                exception=e,
            )
        except Exception as e:
            return self._make_api_result(
                success=False,
                message=f"停止失败: {str(e)}",
                code=500,
                error_type="exception",
                exception=e,
            )

    def delete_container(self, confirm: bool = True, reason: str = "") -> APIResult:
        """删除云电脑"""
        try:
            data = self._request(
                "DELETE", "/container", json={"confirm": confirm, "reason": reason}
            )
            return self._make_api_result(
                success=True, data=data.get("data"), message="删除成功"
            )
        except APIError as e:
            return self._make_api_result(
                success=False,
                message=e.message,
                code=e.code,
                request_id=e.request_id,
                error_type=e.error_type,
                error_detail=e.response,
                exception=e,
            )
        except Exception as e:
            return self._make_api_result(
                success=False,
                message=f"删除失败: {str(e)}",
                code=500,
                error_type="exception",
                exception=e,
            )

    def get_container_info(self) -> APIResult:
        """获取云电脑详细信息（包含UHostId和密码）"""
        try:
            data = self._request("GET", "/container/my/info")
            return self._make_api_result(
                success=True, data=data.get("data"), message="获取成功"
            )
        except APIError as e:
            return self._make_api_result(
                success=False,
                message=e.message,
                code=e.code,
                request_id=e.request_id,
                error_type=e.error_type,
                error_detail=e.response,
                exception=e,
            )
        except Exception as e:
            return self._make_api_result(
                success=False,
                message=f"获取失败: {str(e)}",
                code=500,
                error_type="exception",
                exception=e,
            )

    # ==================== 计费接口 ====================

    def get_billing_statistics(self) -> APIResult:
        """获取消费统计"""
        try:
            data = self._request("GET", "/billing/statistics")
            return self._make_api_result(
                success=True, data=data.get("data"), message="获取成功"
            )
        except APIError as e:
            return self._make_api_result(
                success=False,
                message=e.message,
                code=e.code,
                request_id=e.request_id,
                error_type=e.error_type,
                error_detail=e.response,
                exception=e,
            )
        except Exception as e:
            return self._make_api_result(
                success=False,
                message=f"获取失败: {str(e)}",
                code=500,
                error_type="exception",
                exception=e,
            )

    def get_billing_history(self, page: int = 1, page_size: int = 20) -> APIResult:
        """获取消费历史"""
        try:
            data = self._request(
                "GET", "/billing/history", params={"page": page, "page_size": page_size}
            )
            return self._make_api_result(
                success=True, data=data.get("data"), message="获取成功"
            )
        except APIError as e:
            return self._make_api_result(
                success=False,
                message=e.message,
                code=e.code,
                request_id=e.request_id,
                error_type=e.error_type,
                error_detail=e.response,
                exception=e,
            )
        except Exception as e:
            return self._make_api_result(
                success=False,
                message=f"获取失败: {str(e)}",
                code=500,
                error_type="exception",
                exception=e,
            )

    def get_current_session(self) -> APIResult:
        """获取当前会话计费信息"""
        try:
            data = self._request("GET", "/billing/current-session")
            return self._make_api_result(
                success=True, data=data.get("data"), message="获取成功"
            )
        except APIError as e:
            return self._make_api_result(
                success=False,
                message=e.message,
                code=e.code,
                request_id=e.request_id,
                error_type=e.error_type,
                error_detail=e.response,
                exception=e,
            )
        except Exception as e:
            return self._make_api_result(
                success=False,
                message=f"获取失败: {str(e)}",
                code=500,
                error_type="exception",
                exception=e,
            )


# 全局API客户端实例
api_client = APIClient()
