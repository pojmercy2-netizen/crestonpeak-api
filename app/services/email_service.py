# === FILENAME: app/core/email.py ===

from typing import Any, Dict, List, Optional
from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from app.config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME or "",
    MAIL_PASSWORD=settings.MAIL_PASSWORD or "",
    MAIL_FROM=settings.MAIL_FROM or "noreply@nobleedgeroi.com",
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER or "",
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=Path(__file__).parent.parent.parent / "templates" / "email",
)

fastmail = FastMail(conf)


async def send_email(
    email_to: str,
    subject: str,
    template_name: str,
    template_body: Dict[str, Any],
    bcc: Optional[List[str]] = None,
) -> None:
    try:
        message = MessageSchema(
            subject=subject,
            recipients=[email_to],
            bcc=bcc or [],
            template_body=template_body,
            subtype=MessageType.html,
        )
        await fastmail.send_message(message, template_name=template_name)
    except Exception as e:
        print(f"[email_service] send_email failed (non-fatal): {e}")


# async def send_verification_email(email: str, token: str, name: str) -> None:
#     await send_email(
#         email_to=email,
#         subject="Verify your Gemini Reliance Account",
#         template_name="verification.html",
#         template_body={
#             "project_name": settings.APP_NAME,
#             "name": name,
#             "link": f"{settings.FRONTEND_URL}/auth/verify?token={token}",
#         },
#     )


async def send_welcome_email(email: str, name: str) -> None:
    await send_email(
        email_to=email,
        subject=f"Welcome to {settings.APP_NAME} — Your Account Is Ready",
        template_name="welcome.html",
        template_body={
            "project_name": settings.APP_NAME,
            "name": name,
            "login_url": f"{settings.FRONTEND_URL}/auth/login",
        },
    )


async def send_plain_email(
    email_to: str,
    subject: str,
    body: str,
) -> None:
    try:
        message = MessageSchema(
            subject=subject,
            recipients=[email_to],
            body=body,
            subtype=MessageType.html,
        )
        await fastmail.send_message(message)
    except Exception as e:
        print(f"[email_service] send_plain_email failed (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Transaction initiated (deposit or withdrawal) → user + admin BCC
# ---------------------------------------------------------------------------
async def send_transaction_initiated_email(
    email: str,
    name: str,
    tx_type: str,          # "deposit" | "withdrawal"
    amount: float,
    currency: str,
    reference: str,
    status: str,
    note: Optional[str] = None,
) -> None:
    admin_email = str(settings.ADMIN_EMAIL)
    await send_email(
        email_to=email,
        subject=f"Transaction Initiated — {tx_type.capitalize()} of ${amount:,.2f}",
        template_name="transaction_initiated.html",
        bcc=[admin_email] if admin_email != email else [],
        template_body={
            "project_name": settings.APP_NAME,
            "name": name,
            "tx_type": tx_type.capitalize(),
            "amount": f"{amount:,.2f}",
            "currency": currency,
            "reference": reference,
            "status": status.capitalize(),
            "note": note or "",
            "dashboard_url": f"{settings.FRONTEND_URL}/dashboard/transactions",
        },
    )


# ---------------------------------------------------------------------------
# Transaction approved → user only
# ---------------------------------------------------------------------------
async def send_transaction_approved_email(
    email: str,
    name: str,
    tx_type: str,          # "deposit" | "withdrawal"
    amount: float,
    currency: str,
    reference: str,
) -> None:
    await send_email(
        email_to=email,
        subject=f"Transaction Approved — {tx_type.capitalize()} of ${amount:,.2f}",
        template_name="transaction_approved.html",
        template_body={
            "project_name": settings.APP_NAME,
            "name": name,
            "tx_type": tx_type.capitalize(),
            "amount": f"{amount:,.2f}",
            "currency": currency,
            "reference": reference,
            "dashboard_url": f"{settings.FRONTEND_URL}/dashboard/transactions",
        },
    )


# ---------------------------------------------------------------------------
# Investment ROI return (daily credit OR plan completion)
# ---------------------------------------------------------------------------
async def send_investment_roi_email(
    email: str,
    name: str,
    plan_name: str,
    roi_amount: float,
    total_returned: float,
    amount_invested: float,
    currency: str,
    is_completed: bool = False,
) -> None:
    subject = (
        f"Investment Completed — ${total_returned:,.2f} Total Earned"
        if is_completed
        else f"ROI Credited — ${roi_amount:,.2f} from {plan_name}"
    )
    await send_email(
        email_to=email,
        subject=subject,
        template_name="investment_roi.html",
        template_body={
            "project_name": settings.APP_NAME,
            "name": name,
            "plan_name": plan_name,
            "roi_amount": f"{roi_amount:,.2f}",
            "total_returned": f"{total_returned:,.2f}",
            "amount_invested": f"{amount_invested:,.2f}",
            "currency": currency,
            "is_completed": is_completed,
            "dashboard_url": f"{settings.FRONTEND_URL}/dashboard/investments",
        },
    )


# ---------------------------------------------------------------------------
# Investment notification (new investment purchased) → user + admin BCC
# ---------------------------------------------------------------------------
async def send_investment_notification_email(
    email: str,
    name: str,
    plan_name: str,
    plan_description: str,
    amount_invested: float,
    daily_return_percent: float,
    duration_days: int,
    expected_total: float,
    currency: str,
    start_date: str,
    end_date: str,
) -> None:
    admin_email = str(settings.ADMIN_EMAIL)
    await send_email(
        email_to=email,
        subject=f"Investment Confirmed — {plan_name} Plan",
        template_name="investment_notification.html",
        bcc=[admin_email] if admin_email != email else [],
        template_body={
            "project_name": settings.APP_NAME,
            "name": name,
            "plan_name": plan_name,
            "plan_description": plan_description,
            "amount_invested": f"{amount_invested:,.2f}",
            "daily_return_percent": f"{daily_return_percent:.2f}",
            "duration_days": duration_days,
            "expected_total": f"{expected_total:,.2f}",
            "currency": currency,
            "start_date": start_date,
            "end_date": end_date,
            "dashboard_url": f"{settings.FRONTEND_URL}/dashboard/investments",
        },
    )

# ---------------------------------------------------------------------------
# User Activity Notification (Admin only)
# ---------------------------------------------------------------------------
async def send_admin_activity_notification(
    email: str,
    name: str,
    activity_type: str,
    ip_address: Optional[str] = None,
) -> None:
    admin_email = str(settings.ADMIN_EMAIL)
    body = f"<p>Hello Admin,</p><p>User <strong>{name}</strong> ({email}) has just <strong>{activity_type}</strong>.</p>"
    if ip_address:
        body += f"<p>IP Address: {ip_address}</p>"
    body += f"<br/><p>View their profile in the <a href='{settings.FRONTEND_URL}/admin/users'>Admin Dashboard</a>.</p>"

    try:
        message = MessageSchema(
            subject=f"User Activity Alert: {name} {activity_type}",
            recipients=[admin_email],
            body=body,
            subtype=MessageType.html,
        )
        await fastmail.send_message(message)
    except Exception as e:
        print(f"[email_service] send_admin_activity_notification failed (non-fatal): {e}")


async def send_password_reset_email(email: str, token: str, name: str) -> None:
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    body = f"""
    <div style="font-family: sans-serif; padding: 20px; max-width: 600px; margin: auto; border: 1px solid #e2e8f0; border-radius: 8px;">
        <h2 style="color: #2E5B46;">Password Reset Request</h2>
        <p>Hello {name},</p>
        <p>We received a request to reset your password for your {settings.APP_NAME} account.</p>
        <p>Please click the button below to reset your password. This link is valid for 1 hour.</p>
        <div style="margin: 30px 0; text-align: center;">
            <a href="{reset_url}" style="background-color: #2E5B46; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Reset Password</a>
        </div>
        <p>If you did not request a password reset, you can safely ignore this email.</p>
        <p>Best regards,<br/>The {settings.APP_NAME} Team</p>
    </div>
    """
    await send_plain_email(email_to=email, subject=f"Reset your {settings.APP_NAME} Password", body=body)

