from fastapi import APIRouter, Depends, Request, BackgroundTasks, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.auth import Login, Register, PasswordResetRequest, PasswordReset
from app.services.auth_service import register_user, authenticate_user
from app.dependencies import get_db
from app.services.email_service import send_welcome_email, send_admin_activity_notification, send_password_reset_email
from app.security.hashing import get_password_hash
from datetime import datetime, timezone, timedelta
import uuid
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.user import User

router = APIRouter()

@router.post("/register")
async def register(user_in: Register, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    user = await register_user(db, user_in)
    name = user.full_name if hasattr(user, "full_name") and user.full_name else user.username
    background_tasks.add_task(send_welcome_email, email=user.email, name=name)
    return {
        "success": True,
        "message": "User registered successfully",
        "data": {"id": str(user.id), "email": user.email}
    }

@router.post("/login")
async def login(login_data: Login, request: Request, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    access_token, refresh_token = await authenticate_user(db, login_data, ip_address, user_agent)
    
    # Notify admin
    user_query = await db.execute(select(User).where(User.email == login_data.email))
    user = user_query.scalars().first()
    if user and user.role != "admin" and user.role != "superadmin":
        name = user.full_name if hasattr(user, "full_name") and user.full_name else user.username
        background_tasks.add_task(
            send_admin_activity_notification,
            email=user.email,
            name=name,
            activity_type="logged into their account",
            ip_address=ip_address
        )
    return {
        "success": True,
        "message": "Login successful",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    }

@router.post("/forgot-password")
async def forgot_password(request_data: PasswordResetRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    # Find user by email
    query = await db.execute(select(User).where(func.lower(User.email) == request_data.email.lower()))
    user = query.scalars().first()
    
    if user:
        # Generate token
        token = str(uuid.uuid4())
        user.password_reset_token = token
        user.password_reset_expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
        db.add(user)
        await db.commit()
        
        name = user.full_name if hasattr(user, "full_name") and user.full_name else user.username
        background_tasks.add_task(
            send_password_reset_email,
            email=user.email,
            token=token,
            name=name
        )
        
    return {
        "success": True,
        "message": "If an account with that email exists, a password reset link has been sent."
    }

@router.post("/reset-password")
async def reset_password(reset_data: PasswordReset, db: AsyncSession = Depends(get_db)):
    query = await db.execute(
        select(User).where(
            User.password_reset_token == reset_data.token
        )
    )
    user = query.scalars().first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token."
        )
        
    if user.password_reset_expires and user.password_reset_expires < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired."
        )
        
    # Reset password
    user.password_hash = get_password_hash(reset_data.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.add(user)
    await db.commit()
    
    return {
        "success": True,
        "message": "Your password has been successfully reset. You can now log in."
    }

