import logging
from email.message import EmailMessage

import aiosmtplib

from src.config import settings

logger = logging.getLogger(__name__)

_VERIFICATION_HTML = """\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Verificá tu cuenta &mdash; MicroTV</title>
</head>
<body style="font-family:Arial,sans-serif;background-color:#f4f4f5;margin:0;padding:32px 16px;">
  <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,.08);">
    <div style="background:#dc2626;padding:28px 32px;">
      <h1 style="color:#fff;margin:0;font-size:22px;font-weight:700;">MicroTV</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#111827;margin:0 0 16px;font-size:18px;">Verificá tu cuenta</h2>
      <p style="color:#6b7280;font-size:15px;line-height:1.6;margin:0 0 24px;">
        Hola <strong>{display_name}</strong>,<br><br>
        Gracias por registrarte en MicroTV. Para activar tu cuenta, hacé clic en el botón de abajo.
      </p>
      <a href="{verification_url}"
         style="display:inline-block;background:#dc2626;color:#fff;font-weight:600;font-size:15px;text-decoration:none;padding:12px 28px;border-radius:8px;">
        Verificar mi cuenta
      </a>
      <p style="color:#9ca3af;font-size:13px;margin:28px 0 0;line-height:1.5;">
        Este link vence en 24 horas. Si no creaste esta cuenta, podés ignorar este email.<br><br>
        O copiá este link en tu navegador:<br>
        <a href="{verification_url}" style="color:#dc2626;word-break:break-all;">{verification_url}</a>
      </p>
    </div>
  </div>
</body>
</html>
"""

_VERIFICATION_TEXT = """\
Verificá tu cuenta en MicroTV

Hola {display_name},

Gracias por registrarte en MicroTV. Para activar tu cuenta, visitá el siguiente link:

{verification_url}

Este link vence en 24 horas. Si no creaste esta cuenta, podés ignorar este email.

— El equipo de MicroTV
"""

_PASSWORD_RESET_HTML = """\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Restablecé tu contraseña &mdash; MicroTV</title>
</head>
<body style="font-family:Arial,sans-serif;background-color:#f4f4f5;margin:0;padding:32px 16px;">
  <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,.08);">
    <div style="background:#dc2626;padding:28px 32px;">
      <h1 style="color:#fff;margin:0;font-size:22px;font-weight:700;">MicroTV</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#111827;margin:0 0 16px;font-size:18px;">Restablecé tu contraseña</h2>
      <p style="color:#6b7280;font-size:15px;line-height:1.6;margin:0 0 24px;">
        Hola <strong>{display_name}</strong>,<br><br>
        Recibimos una solicitud para restablecer la contraseña de tu cuenta en MicroTV.
      </p>
      <a href="{reset_url}"
         style="display:inline-block;background:#dc2626;color:#fff;font-weight:600;font-size:15px;text-decoration:none;padding:12px 28px;border-radius:8px;">
        Crear nueva contraseña
      </a>
      <p style="color:#9ca3af;font-size:13px;margin:28px 0 0;line-height:1.5;">
        Este link vence en {expires_minutes} minutos. Si no solicitaste este cambio, podés ignorar este email.<br><br>
        O copiá este link en tu navegador:<br>
        <a href="{reset_url}" style="color:#dc2626;word-break:break-all;">{reset_url}</a>
      </p>
    </div>
  </div>
</body>
</html>
"""

_PASSWORD_RESET_TEXT = """\
Restablecé tu contraseña en MicroTV

Hola {display_name},

Recibimos una solicitud para restablecer la contraseña de tu cuenta en MicroTV.

Usá el siguiente link para crear una nueva contraseña:

{reset_url}

Este link vence en {expires_minutes} minutos. Si no solicitaste este cambio, podés ignorar este email.

— El equipo de MicroTV
"""


async def send_verification_email(
    to_email: str,
    display_name: str,
    verification_token: str,
) -> None:
    """
    Send an email verification message.

    If SMTP credentials are not configured (dev mode), logs the verification
    URL and skips the actual send so developers can complete the flow locally.

    SMTP errors are logged and re-raised so callers can decide whether to block
    the request or absorb the failure.
    """
    verification_url = f"{settings.frontend_url}/verify-email?token={verification_token}"

    if not settings.smtp_user or not settings.smtp_password:
        logger.warning(
            "SMTP not configured — skipping email send. "
            "Use this URL to verify manually: %s",
            verification_url,
        )
        return

    html_body = _VERIFICATION_HTML.format(
        display_name=display_name,
        verification_url=verification_url,
    )
    text_body = _VERIFICATION_TEXT.format(
        display_name=display_name,
        verification_url=verification_url,
    )

    message = EmailMessage()
    message["Subject"] = "Verificá tu cuenta en MicroTV"
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from}>"
    message["To"] = to_email
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )


async def send_password_reset_email(
    to_email: str,
    display_name: str,
    reset_token: str,
    expires_minutes: int = 60,
) -> None:
    """
    Send a password reset email.

    If SMTP credentials are not configured (dev mode), logs the reset URL and
    skips the actual send so developers can complete the flow locally.
    """
    reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"

    if not settings.smtp_user or not settings.smtp_password:
        logger.warning(
            "SMTP not configured — skipping password reset email. "
            "Use this URL to reset manually: %s",
            reset_url,
        )
        return

    html_body = _PASSWORD_RESET_HTML.format(
        display_name=display_name,
        reset_url=reset_url,
        expires_minutes=expires_minutes,
    )
    text_body = _PASSWORD_RESET_TEXT.format(
        display_name=display_name,
        reset_url=reset_url,
        expires_minutes=expires_minutes,
    )

    message = EmailMessage()
    message["Subject"] = "Restablecé tu contraseña en MicroTV"
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from}>"
    message["To"] = to_email
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )


# ── Company admin invitation email ────────────────────────────────────────────

_INVITATION_HTML = """\
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Invitación a administrar {company_name} &mdash; MicroTV</title>
</head>
<body style="font-family:Arial,sans-serif;background-color:#f4f4f5;margin:0;padding:32px 16px;">
  <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,.08);">
    <div style="background:#dc2626;padding:28px 32px;">
      <h1 style="color:#fff;margin:0;font-size:22px;font-weight:700;">MicroTV</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#111827;margin:0 0 16px;font-size:18px;">Te invitaron a administrar {company_name}</h2>
      <p style="color:#6b7280;font-size:15px;line-height:1.6;margin:0 0 24px;">
        Recibiste una invitación para ser administrador de <strong>{company_name}</strong>
        en la plataforma MicroTV.<br><br>
        Para aceptar la invitación y crear tu cuenta, hacé clic en el botón de abajo.
        Esta invitación vence en <strong>{expires_hours} horas</strong>.
      </p>
      <a href="{invitation_url}"
         style="display:inline-block;background:#dc2626;color:#fff;font-weight:600;font-size:15px;text-decoration:none;padding:12px 28px;border-radius:8px;">
        Aceptar invitación
      </a>
      <p style="color:#9ca3af;font-size:13px;margin:28px 0 0;line-height:1.5;">
        Si no esperabas esta invitación, podés ignorar este email.<br><br>
        O copiá este link en tu navegador:<br>
        <a href="{invitation_url}" style="color:#dc2626;word-break:break-all;">{invitation_url}</a>
      </p>
    </div>
  </div>
</body>
</html>
"""

_INVITATION_TEXT = """\
Invitación a administrar {company_name} — MicroTV

Te invitaron a ser administrador de {company_name} en la plataforma MicroTV.

Para aceptar la invitación y crear tu cuenta, visitá el siguiente link:

{invitation_url}

Esta invitación vence en {expires_hours} horas.

Si no esperabas esta invitación, podés ignorar este email.

— El equipo de MicroTV
"""


async def send_company_admin_invitation(
    email: str,
    company_name: str,
    invitation_token: str,
    expires_hours: int = 48,
) -> None:
    """
    Send a company_admin invitation email.

    If SMTP credentials are not configured (dev mode), logs the invitation
    URL and skips the actual send.
    """
    invitation_url = f"{settings.saas_base_url}/accept-invitation?token={invitation_token}"

    if not settings.smtp_user or not settings.smtp_password:
        logger.warning(
            "SMTP not configured — skipping invitation email. "
            "Use this URL to accept manually: %s",
            invitation_url,
        )
        return

    html_body = _INVITATION_HTML.format(
        company_name=company_name,
        invitation_url=invitation_url,
        expires_hours=expires_hours,
    )
    text_body = _INVITATION_TEXT.format(
        company_name=company_name,
        invitation_url=invitation_url,
        expires_hours=expires_hours,
    )

    message = EmailMessage()
    message["Subject"] = f"Invitación para administrar {company_name} en MicroTV"
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from}>"
    message["To"] = email
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user,
        password=settings.smtp_password,
        start_tls=True,
    )

