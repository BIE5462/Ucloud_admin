from datetime import datetime, timezone, timedelta


# 北京时间时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))


def format_datetime_beijing(dt: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """将datetime转换为北京时间并格式化

    Args:
        dt: datetime对象（可以是带时区或不带时区的）
        fmt: 格式化字符串

    Returns:
        格式化后的北京时间字符串
    """
    if not dt:
        return None

    # 如果datetime没有时区信息，假设它是UTC时间
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # 转换为北京时间
    beijing_time = dt.astimezone(BEIJING_TZ)
    return beijing_time.strftime(fmt)


def get_now_beijing() -> datetime:
    """获取当前北京时间"""
    return datetime.now(timezone.utc).astimezone(BEIJING_TZ)


def utc_to_beijing(dt: datetime) -> datetime:
    """将UTC时间转换为北京时间"""
    if not dt:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(BEIJING_TZ)
