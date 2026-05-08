import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_super_admin
from app.db.database import get_db
from app.schemas.schemas import (
    CloudServerCreate,
    CloudServerInfo,
    CloudServerUpdate,
    ResponseData,
)
from app.services.crud_service import cloud_server_service, log_service

router = APIRouter(prefix="/admin/servers", tags=["服务器管理"])


def _server_payload(server) -> dict:
    return CloudServerInfo(**cloud_server_service.serialize(server)).model_dump()


@router.get("", response_model=ResponseData)
async def list_servers(
    current_admin=Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取服务器列表"""
    servers = await cloud_server_service.list_servers(db)
    return ResponseData(
        code=200,
        message="success",
        data={"items": [_server_payload(server) for server in servers]},
    )


@router.post("", response_model=ResponseData)
async def create_server(
    server_data: CloudServerCreate,
    current_admin=Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建服务器"""
    existing = await cloud_server_service.get_by_name(db, server_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="服务器名称已存在"
        )

    try:
        server = await cloud_server_service.create(
            db, server_data.model_dump(), current_admin.id
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="服务器名称已存在"
        ) from exc

    await log_service.create_admin_operation_log(
        db,
        current_admin.id,
        "create_server",
        "server",
        server.id,
        new_value=json.dumps(_server_payload(server), ensure_ascii=False),
        description=f"创建服务器: {server.name}",
    )

    return ResponseData(code=200, message="创建成功", data=_server_payload(server))


@router.put("/{server_id}", response_model=ResponseData)
async def update_server(
    server_id: int,
    server_data: CloudServerUpdate,
    current_admin=Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新服务器"""
    server = await cloud_server_service.get_by_id(db, server_id)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="服务器不存在"
        )

    existing = await cloud_server_service.get_by_name(db, server_data.name)
    if existing and existing.id != server_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="服务器名称已存在"
        )

    old_value = _server_payload(server)
    try:
        server = await cloud_server_service.update(
            db, server, server_data.model_dump(), current_admin.id
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="服务器名称已存在"
        ) from exc

    await log_service.create_admin_operation_log(
        db,
        current_admin.id,
        "update_server",
        "server",
        server.id,
        old_value=json.dumps(old_value, ensure_ascii=False),
        new_value=json.dumps(_server_payload(server), ensure_ascii=False),
        description=f"更新服务器: {server.name}",
    )

    return ResponseData(code=200, message="更新成功", data=_server_payload(server))


@router.delete("/{server_id}", response_model=ResponseData)
async def delete_server(
    server_id: int,
    current_admin=Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除服务器"""
    server = await cloud_server_service.get_by_id(db, server_id)
    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="服务器不存在"
        )

    if await cloud_server_service.has_active_containers(db, server_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该服务器仍有关联云电脑，不能删除",
        )

    old_value = _server_payload(server)
    server_name = server.name
    await cloud_server_service.delete(db, server)
    await log_service.create_admin_operation_log(
        db,
        current_admin.id,
        "delete_server",
        "server",
        server_id,
        old_value=json.dumps(old_value, ensure_ascii=False),
        description=f"删除服务器: {server_name}",
    )

    return ResponseData(code=200, message="删除成功")
