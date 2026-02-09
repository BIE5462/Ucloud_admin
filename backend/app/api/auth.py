from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.db.database import get_db
from app.core.security import (
    verify_password,
    create_access_token,
    decode_token,
    get_password_hash,
)
from app.schemas.schemas import UserLogin, AdminLogin, ResponseData, UserInfo, AdminInfo
from app.services.crud_service import user_service, admin_service
from app.models.models import User, Admin

router = APIRouter(prefix="/auth", tags=["认证"])
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """获取当前用户"""
    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的Token"
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的Token"
        )

    user = await user_service.get_by_id(db, user_id)
    if not user or user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已被禁用"
        )

    return user


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Admin:
    """获取当前管理员"""
    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的Token"
        )

    admin_id = payload.get("admin_id")
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的Token"
        )

    admin = await admin_service.get_by_id(db, admin_id)
    if not admin or admin.status != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="管理员不存在或已被禁用"
        )

    return admin


async def get_current_super_admin(
    current_admin: Admin = Depends(get_current_admin),
) -> Admin:
    """获取当前超级管理员"""
    if current_admin.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要超级管理员权限"
        )
    return current_admin


@router.post("/login", response_model=ResponseData)
async def user_login(
    login_data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)
):
    """用户登录"""
    user = await user_service.get_by_phone(db, login_data.phone)

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="手机号或密码错误"
        )

    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用"
        )

    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # 生成Token
    access_token = create_access_token(
        {"user_id": user.id, "phone": user.phone, "type": "user"}
    )

    return ResponseData(
        code=200,
        message="登录成功",
        data={
            "token": access_token,
            "token_type": "Bearer",
            "expires_in": 86400,
            "user": {
                "id": user.id,
                "company_name": user.company_name,
                "contact_name": user.contact_name,
                "phone": user.phone,
                "balance": user.balance,
                "current_container_id": user.current_container_id,
            },
        },
    )


@router.post("/admin/login", response_model=ResponseData)
async def admin_login(
    login_data: AdminLogin, request: Request, db: AsyncSession = Depends(get_db)
):
    """管理员登录"""
    admin = await admin_service.get_by_username(db, login_data.username)

    if not admin or not verify_password(login_data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
        )

    if admin.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用"
        )

    # 更新最后登录时间
    admin.last_login_at = datetime.utcnow()
    admin.last_login_ip = request.client.host
    await db.commit()

    # 生成Token
    access_token = create_access_token(
        {
            "admin_id": admin.id,
            "username": admin.username,
            "role": admin.role,
            "type": "admin",
        }
    )

    return ResponseData(
        code=200,
        message="登录成功",
        data={
            "token": access_token,
            "token_type": "Bearer",
            "expires_in": 86400,
            "admin": {"id": admin.id, "username": admin.username, "role": admin.role},
        },
    )


@router.post("/logout", response_model=ResponseData)
async def logout(current_user: User = Depends(get_current_user)):
    """退出登录"""
    # JWT方式不需要服务器端处理，客户端删除Token即可
    return ResponseData(code=200, message="退出成功")
