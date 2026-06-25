import asyncio
import smtplib
from email.mime.text import MIMEText
from typing import List

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


async def send_alert_notifications(rule_name: str, message: str, severity: str) -> dict:
    """并发发送告警到所有已配置渠道。"""
    results = {"email": False, "serverchan": False, "wechat_work": False}

    tasks = []
    if settings.SMTP_HOST and settings.SMTP_USER and settings.ALERT_EMAIL_TO:
        tasks.append(_send_email(rule_name, message, severity, results))
    if settings.SERVERCHAN_SENDKEY:
        tasks.append(_send_serverchan(rule_name, message, severity, results))
    if settings.WECHAT_WORK_WEBHOOK:
        tasks.append(_send_wechat_work(rule_name, message, severity, results))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

    return results


async def _send_email(rule_name: str, message: str, severity: str, results: dict):
    try:
        recipients = [e.strip() for e in settings.ALERT_EMAIL_TO.split(",") if e.strip()]
        if not recipients:
            return

        subject = f"[泡沫雷达][{severity.upper()}] {rule_name}"
        body = f"告警规则：{rule_name}\n级别：{severity}\n详情：{message}"

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
        msg["To"] = ", ".join(recipients)

        def _send():
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_PORT == 587:
                    server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM or settings.SMTP_USER, recipients, msg.as_string())

        await asyncio.to_thread(_send)
        results["email"] = True
        logger.info("邮件告警已发送", rule=rule_name, recipients=recipients)
    except Exception as exc:
        logger.warning("邮件告警发送失败", rule=rule_name, error=str(exc))


async def _send_serverchan(rule_name: str, message: str, severity: str, results: dict):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://sctapi.ftqq.com/{settings.SERVERCHAN_SENDKEY}.send",
                data={"title": f"[泡沫雷达][{severity.upper()}] {rule_name}", "desp": message},
            )
            resp.raise_for_status()
        results["serverchan"] = True
        logger.info("Server酱告警已发送", rule=rule_name)
    except Exception as exc:
        logger.warning("Server酱告警发送失败", rule=rule_name, error=str(exc))


async def _send_wechat_work(rule_name: str, message: str, severity: str, results: dict):
    try:
        color_map = {"info": "info", "watch": "warning", "warn": "warning", "danger": "red"}
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"**泡沫雷达告警**\n> 规则：{rule_name}\n> 级别：<font color=\"{color_map.get(severity, 'warning')}\">{severity.upper()}</font>\n> 详情：{message}"
            },
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(settings.WECHAT_WORK_WEBHOOK, json=payload)
            resp.raise_for_status()
        results["wechat_work"] = True
        logger.info("企业微信告警已发送", rule=rule_name)
    except Exception as exc:
        logger.warning("企业微信告警发送失败", rule=rule_name, error=str(exc))
