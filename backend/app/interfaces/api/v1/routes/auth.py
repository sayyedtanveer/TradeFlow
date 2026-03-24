from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from backend.app.application.tenant.commands.register_tenant import RegisterTenantCommand
from backend.app.application.tenant.commands.login_user import LoginUserCommand
from backend.app.application.tenant.handlers.register_tenant_handler import RegisterTenantHandler
from backend.app.application.tenant.handlers.login_user_handler import LoginUserHandler
from backend.app.infrastructure.persistence.repositories.tenant_repository import TenantRepository
from backend.app.infrastructure.persistence.repositories.user_repository import UserRepository
from backend.app.infrastructure.persistence.unit_of_work import SQLAlchemyUnitOfWork
from backend.app.interfaces.api.v1.dependencies.auth import (
    get_container,
    get_current_user_payload,
    get_current_tenant_id,
    get_current_user_id,
    get_current_role,
)
from backend.app.interfaces.api.v1.schemas.auth_schemas import (
    LoginRequest,
    LoginResponse,
    RegisterTenantRequest,
    RegisterTenantResponse,
    UserProfileResponse,
    UserInMeResponse,
    TenantInMeResponse,
)
from backend.app.infrastructure.tasks.sample_tasks import SendWelcomeEmailTask

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register-tenant",
    response_model=RegisterTenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new tenant + admin user",
)
async def register_tenant(
    body: RegisterTenantRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    container = get_container(request)
    async with container.session_factory() as session:
        tenant_repo = TenantRepository(session)
        user_repo = UserRepository(session)
        uow = SQLAlchemyUnitOfWork(
            session=session,
            event_dispatcher=container.event_dispatcher,
        )
        handler = RegisterTenantHandler(
            uow=uow,
            tenant_repo=tenant_repo,
            user_repo=user_repo,
            password_hasher=container.password_hasher,
            jwt_handler=container.jwt_handler,
        )
        command = RegisterTenantCommand(
            name=body.name,
            slug=body.slug,
            admin_email=body.admin_email,
            admin_password=body.admin_password,
            admin_first_name=body.admin_first_name,
            admin_last_name=body.admin_last_name,
            plan=body.plan,
        )
        result = await handler.handle(command)

    # Enqueue welcome email as background task
    container.task_service.enqueue(
        SendWelcomeEmailTask(
            email=result.email,
            tenant_name=result.tenant_name,
            first_name=body.admin_first_name,
        ),
        bg_tasks=background_tasks,
    )

    return RegisterTenantResponse(
        tenant_id=result.tenant_id,
        tenant_name=result.tenant_name,
        slug=result.slug,
        user_id=result.user_id,
        email=result.email,
        role=result.role,
        access_token=result.access_token,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate and get JWT token",
)
async def login(body: LoginRequest, request: Request):
    container = get_container(request)
    async with container.session_factory() as session:
        user_repo = UserRepository(session)
        handler = LoginUserHandler(
            user_repo=user_repo,
            password_hasher=container.password_hasher,
            jwt_handler=container.jwt_handler,
        )
        try:
            tenant_id = uuid.UUID(body.tenant_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid tenant_id format")

        command = LoginUserCommand(
            email=body.email,
            password=body.password,
            tenant_id=tenant_id,
        )
        result = await handler.handle(command)

    return LoginResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        user_id=result.user_id,
        tenant_id=result.tenant_id,
        email=result.email,
        role=result.role,
        full_name=result.full_name,
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current authenticated user profile + tenant info",
)
async def me(
    request: Request,
    payload: dict = Depends(get_current_user_payload),
):
    container = get_container(request)
    tenant_id_str = payload.get("tid", "")
    user_id_str   = payload.get("sub", "")

    try:
        tenant_id = uuid.UUID(tenant_id_str)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: bad tenant_id")

    async with container.session_factory() as session:
        tenant_repo = TenantRepository(session)
        tenant = await tenant_repo.get_by_tenant_id(tenant_id)

    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    full_name  = payload.get("full_name", "")
    parts      = full_name.split(" ", 1) if full_name else ["", ""]
    first_name = parts[0]
    last_name  = parts[1] if len(parts) > 1 else ""

    return UserProfileResponse(
        user=UserInMeResponse(
            id=user_id_str,
            email=payload.get("email", ""),
            first_name=first_name,
            last_name=last_name,
            role=payload.get("role", "viewer"),
            tenant_id=tenant_id_str,
            is_active=True,
        ),
        tenant=TenantInMeResponse(
            id=str(tenant.id),
            name=tenant.name,
            slug=tenant.slug,
            plan=tenant.plan,
            is_active=tenant.is_active,
        ),
        permissions=[],
    )

