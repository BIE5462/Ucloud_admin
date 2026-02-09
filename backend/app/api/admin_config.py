from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.auth import get_current_admin, get_current_super_admin
from app.schemas.schemas import ResponseData, SystemConfigUpdate, SystemConfigInfo
from app.services.crud_service import config_service, log_service
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/admin/config", tags=["系统配置"])


@router.get("", response_model=ResponseData)
async def get_system_config(
    current_admin=Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    """获取系统配置"""
    configs = await config_service.get_all_configs(db)

    return ResponseData(
        code=200,
        message="success",
        data={
            "price_per_minute": float(
                configs.get("price_per_minute", settings.DEFAULT_PRICE_PER_MINUTE)
            ),
            "min_balance_to_start": float(
                configs.get(
                    "min_balance_to_start", settings.DEFAULT_MIN_BALANCE_TO_START
                )
            ),
            "auto_stop_threshold": float(configs.get("auto_stop_threshold", 0.0)),
        },
    )


@router.put("/price", response_model=ResponseData)
async def update_price(
    config_update: SystemConfigUpdate,
    current_admin=Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新每分钟价格（仅超级管理员）"""
    if config_update.price_per_minute <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="价格必须大于0"
        )

    # 获取旧价格
    old_price = await config_service.get_price_per_minute(db)

    # 更新配置
    await config_service.set_config(
        db,
        "price_per_minute",
        str(config_update.price_per_minute),
        description="云电脑每分钟价格（元）",
        updated_by=current_admin.id,
    )

    # 记录日志
    await log_service.create_admin_operation_log(
        db,
        current_admin.id,
        "update_price",
        "config",
        None,
        old_value=str(old_price),
        new_value=str(config_update.price_per_minute),
        description=f"更新每分钟价格: {old_price} -> {config_update.price_per_minute}",
    )

    return ResponseData(
        code=200,
        message="价格更新成功",
        data={
            "old_price": old_price,
            "new_price": config_update.price_per_minute,
            "affected_containers": 0,
            "note": "价格更新只影响新创建的实例，已创建实例保持创建时的价格",
        },
    )
