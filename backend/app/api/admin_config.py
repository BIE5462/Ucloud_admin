import json

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_admin, get_current_super_admin
from app.db.database import get_db
from app.schemas.schemas import ResponseData, SystemConfigInfo, SystemConfigUpdate
from app.services.crud_service import config_service, log_service

router = APIRouter(prefix="/admin/config", tags=["系统配置"])


async def _save_system_configs(
    db: AsyncSession,
    config_data: dict,
    admin_id: int,
    action: str,
    description: str,
) -> dict:
    """保存系统配置并记录日志"""
    old_configs = await config_service.get_all_configs(db)

    await config_service.set_configs(
        db,
        config_data,
        updated_by=admin_id,
    )

    new_configs = await config_service.get_all_configs(db)

    await log_service.create_admin_operation_log(
        db,
        admin_id,
        action,
        "config",
        None,
        old_value=json.dumps(old_configs, ensure_ascii=False),
        new_value=json.dumps(new_configs, ensure_ascii=False),
        description=description,
    )

    return new_configs


@router.get("", response_model=ResponseData)
async def get_system_config(
    current_admin=Depends(get_current_admin), db: AsyncSession = Depends(get_db)
):
    """获取系统配置"""
    configs = await config_service.get_all_configs(db)
    config_info = SystemConfigInfo(**configs)

    return ResponseData(
        code=200,
        message="success",
        data=config_info.model_dump(),
    )


@router.put("", response_model=ResponseData)
async def update_system_config(
    config_update: SystemConfigUpdate,
    current_admin=Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新系统配置（仅超级管理员）"""
    config_data = config_update.model_dump()
    new_configs = await _save_system_configs(
        db,
        config_data,
        current_admin.id,
        action="update_system_config",
        description="更新系统配置",
    )

    return ResponseData(
        code=200,
        message="系统配置更新成功",
        data=SystemConfigInfo(**new_configs).model_dump(),
    )


@router.put("/price", response_model=ResponseData)
async def update_price(
    price_per_minute: float = Body(embed=True, gt=0),
    current_admin=Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """兼容旧版价格更新接口（仅超级管理员）"""
    configs = await config_service.get_all_configs(db)
    config_update = SystemConfigUpdate(
        min_balance_to_start=configs["min_balance_to_start"],
        auto_stop_threshold=configs["auto_stop_threshold"],
        comp_share_image_id=configs["comp_share_image_id"],
        config_prices=[
            {
                "config_code": item["config_code"],
                "price_per_minute": price_per_minute,
            }
            for item in configs["config_options"]
        ],
    )

    new_configs = await _save_system_configs(
        db,
        config_update.model_dump(),
        current_admin.id,
        action="update_price",
        description=f"更新每分钟价格为: {price_per_minute}",
    )

    return ResponseData(
        code=200,
        message="价格更新成功",
        data={
            "old_price": configs["price_per_minute"],
            "new_price": new_configs["price_per_minute"],
            "affected_containers": 0,
            "note": "价格更新只影响新创建的实例，已创建实例保持创建时的价格",
        },
    )
