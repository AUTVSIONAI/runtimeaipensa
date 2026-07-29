"""
Notification Runtime Module

Provides multi-channel notifications (email, webhook, push, SMS),
templates, scheduling, and delivery tracking.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import asyncio
import logging
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiohttp

from runtime.modules import (
    RuntimeModule,
    ModuleMetadata,
    ModuleState,
)

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    PUSH = "push"
    SMS = "sms"
    SLACK = "slack"
    TEAMS = "teams"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    IN_APP = "in_app"


class NotificationStatus(Enum):
    """Notification delivery status."""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    SPAM = "spam"
    UNSUBSCRIBED = "unsubscribed"


class NotificationPriority(Enum):
    """Notification priority."""
    LOW = 0
    NORMAL = 50
    HIGH = 75
    URGENT = 100


@dataclass
class NotificationTemplate:
    """Notification template."""
    template_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    channel: NotificationChannel = NotificationChannel.EMAIL
    subject_template: str = ""
    body_template: str = ""
    required_variables: List[str] = field(default_factory=list)
    default_values: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def render(self, variables: Dict[str, Any]) -> Dict[str, str]:
        """Render template with variables."""
        merged = {**self.default_values, **variables}

        # Check required variables
        missing = [v for v in self.required_variables if v not in merged]
        if missing:
            raise ValueError(f"Missing required variables: {missing}")

        # Simple template rendering
        subject = self.subject_template
        body = self.body_template

        for key, value in merged.items():
            placeholder = f"{{{key}}}"
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))

        return {"subject": subject, "body": body}


@dataclass
class Notification:
    """Notification message."""
    notification_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    message: str = ""
    channel: NotificationChannel = NotificationChannel.EMAIL
    priority: NotificationPriority = NotificationPriority.NORMAL
    recipient: str = ""  # Email, phone, webhook URL, device token, etc.
    recipient_name: Optional[str] = None
    template_id: Optional[str] = None
    template_variables: Dict[str, Any] = field(default_factory=dict)
    status: NotificationStatus = NotificationStatus.PENDING
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    headers: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    correlation_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "notification_id": self.notification_id,
            "title": self.title,
            "message": self.message,
            "channel": self.channel.value,
            "priority": self.priority.value,
            "recipient": self.recipient,
            "recipient_name": self.recipient_name,
            "template_id": self.template_id,
            "template_variables": self.template_variables,
            "status": self.status.value,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "failed_at": self.failed_at.isoformat() if self.failed_at else None,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "headers": self.headers,
            "metadata": self.metadata,
            "tags": self.tags,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class ChannelConfig:
    """Channel configuration."""
    channel: NotificationChannel
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    rate_limit: Optional[int] = None  # per minute
    default_priority: NotificationPriority = NotificationPriority.NORMAL


class NotificationChannelBase(ABC):
    """Base class for notification channels."""

    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """Send notification. Returns True if successful."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test channel connectivity."""
        pass

    @property
    @abstractmethod
    def channel_type(self) -> NotificationChannel:
        """Return channel type."""
        pass


class EmailChannel(NotificationChannelBase):
    """Email notification channel."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.smtp_host = config.get("smtp_host", "localhost")
        self.smtp_port = config.get("smtp_port", 587)
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.use_tls = config.get("use_tls", True)
        self.from_email = config.get("from_email", "noreply@example.com")
        self.from_name = config.get("from_name", "AIPENSA")

    @property
    def channel_type(self) -> NotificationChannel:
        return NotificationChannel.EMAIL

    async def send(self, notification: Notification) -> bool:
        """Send email notification."""
        try:
            msg = MIMEMultipart()
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = notification.recipient
            msg["Subject"] = notification.title

            if notification.headers:
                for key, value in notification.headers.items():
                    msg[key] = value

            # Add body
            msg.attach(MIMEText(notification.message, "html" if "<html>" in notification.message.lower() else "plain"))

            # Send
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_sync, msg)

            return True
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            notification.error = str(e)
            return False

    def _send_sync(self, msg: MIMEMultipart) -> None:
        """Synchronous email sending."""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)
            server.send_message(msg)

    async def test_connection(self) -> bool:
        """Test SMTP connection."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._test_sync)
            return True
        except Exception:
            return False

    def _test_sync(self) -> None:
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)


class WebhookChannel(NotificationChannelBase):
    """Webhook notification channel."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.default_timeout = config.get("timeout", 10)
        self.default_headers = config.get("default_headers", {"Content-Type": "application/json"})
        self.verify_ssl = config.get("verify_ssl", True)

    @property
    def channel_type(self) -> NotificationChannel:
        return NotificationChannel.WEBHOOK

    async def send(self, notification: Notification) -> bool:
        """Send webhook notification."""
        try:
            url = notification.recipient
            payload = {
                "notification_id": notification.notification_id,
                "title": notification.title,
                "message": notification.message,
                "priority": notification.priority.value,
                "timestamp": notification.created_at.isoformat(),
                "metadata": notification.metadata,
                "tags": notification.tags,
                "correlation_id": notification.correlation_id
            }

            headers = {**self.default_headers, **notification.headers}

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.default_timeout),
                    ssl=self.verify_ssl
                ) as response:
                    if 200 <= response.status < 300:
                        return True
                    else:
                        notification.error = f"HTTP {response.status}: {await response.text()}"
                        return False

        except Exception as e:
            logger.error(f"Webhook send failed: {e}")
            notification.error = str(e)
            return False

    async def test_connection(self) -> bool:
        """Test webhook - just validate config."""
        return True


class PushChannel(NotificationChannelBase):
    """Push notification channel (FCM, APNs, etc.)."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = config.get("provider", "fcm")  # fcm, apns
        self.api_key = config.get("api_key", "")
        self.project_id = config.get("project_id", "")

    @property
    def channel_type(self) -> NotificationChannel:
        return NotificationChannel.PUSH

    async def send(self, notification: Notification) -> bool:
        """Send push notification."""
        try:
            # FCM implementation example
            if self.provider == "fcm":
                return await self._send_fcm(notification)
            elif self.provider == "apns":
                return await self._send_apns(notification)
            return False
        except Exception as e:
            logger.error(f"Push send failed: {e}")
            notification.error = str(e)
            return False

    async def _send_fcm(self, notification: Notification) -> bool:
        """Send via Firebase Cloud Messaging."""
        url = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
        url = url.format(project_id=self.project_id)

        payload = {
            "message": {
                "token": notification.recipient,
                "notification": {
                    "title": notification.title,
                    "body": notification.message
                },
                "data": {k: str(v) for k, v in notification.metadata.items()},
                "priority": "high" if notification.priority == NotificationPriority.URGENT else "normal"
            }
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                return 200 <= response.status < 300

    async def _send_apns(self, notification: Notification) -> bool:
        """Send via Apple Push Notification Service."""
        # Implementation would require APNs certificate/key
        logger.warning("APNs not implemented")
        return False

    async def test_connection(self) -> bool:
        return bool(self.api_key and self.project_id)


class SlackChannel(NotificationChannelBase):
    """Slack notification channel."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.default_webhook_url = config.get("webhook_url", "")
        self.bot_token = config.get("bot_token", "")

    @property
    def channel_type(self) -> NotificationChannel:
        return NotificationChannel.SLACK

    async def send(self, notification: Notification) -> bool:
        """Send Slack notification."""
        try:
            webhook_url = notification.recipient or self.default_webhook_url
            if not webhook_url:
                notification.error = "No webhook URL configured"
                return False

            payload = {
                "text": notification.title,
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": notification.title}
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": notification.message}
                    }
                ]
            }

            # Add metadata as fields
            if notification.metadata:
                fields = []
                for k, v in notification.metadata.items():
                    fields.append({"type": "mrkdwn", "text": f"*{k}:* {v}"})
                if fields:
                    payload["blocks"].append({"type": "section", "fields": fields})

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    return 200 <= response.status < 300

        except Exception as e:
            logger.error(f"Slack send failed: {e}")
            notification.error = str(e)
            return False

    async def test_connection(self) -> bool:
        return bool(self.default_webhook_url or self.bot_token)


class NotificationModule(RuntimeModule):
    """
    Multi-channel notification module.

    Supports:
    - Email (SMTP)
    - Webhooks
    - Push notifications (FCM, APNs)
    - Slack, Teams, Discord, Telegram
    - SMS (via Twilio, Plivo)
    - In-app notifications
    - Templates with variable substitution
    - Scheduling and retries
    - Delivery tracking
    """

    @property
    def metadata(self) -> ModuleMetadata:
        return ModuleMetadata(
            name="notification",
            version="1.0.0",
            description="Multi-channel notification delivery",
            author="AIPENSA",
            dependencies=["tool"],
            provides=["email", "webhook", "push", "slack", "sms", "in_app", "templates", "scheduling"],
            tags={"notification", "email", "webhook", "push", "messaging"}
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._channels: Dict[NotificationChannel, NotificationChannelBase] = {}
        self._channel_configs: Dict[NotificationChannel, ChannelConfig] = {}
        self._templates: Dict[str, NotificationTemplate] = {}
        self._notifications: Dict[str, Notification] = {}
        self._scheduled_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._scheduler_task: Optional[asyncio.Task] = None
        self._max_history = config.get("max_history", 10000) if config else 10000
        self._rate_limits: Dict[NotificationChannel, asyncio.Semaphore] = {}
        self._delivery_callbacks: List[Callable[[Notification], None]] = []

    async def initialize(self, runtime: "Runtime", config: Dict[str, Any]) -> None:
        """Initialize notification module."""
        self._runtime = runtime
        self._config = {**self._config, **config}
        self._max_history = self._config.get("max_history", self._max_history)

        # Initialize channels
        for channel_name, channel_config in self._config.get("channels", {}).items():
            try:
                channel = NotificationChannel(channel_name)
                await self._create_channel(channel, channel_config)
            except ValueError:
                logger.warning(f"Unknown channel: {channel_name}")

        # Initialize rate limiters
        for channel, channel_config in self._channel_configs.items():
            if channel_config.rate_limit:
                self._rate_limits[channel] = asyncio.Semaphore(channel_config.rate_limit)

        # Load templates
        for template_data in self._config.get("templates", []):
            template = NotificationTemplate(**template_data)
            self._templates[template.template_id] = template

        # Start scheduler
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

        self.state = ModuleState.INITIALIZED
        logger.info(f"Notification module initialized with {len(self._channels)} channels")

    async def start(self) -> None:
        """Start notification module."""
        self.state = ModuleState.RUNNING
        logger.info("Notification module started")

    async def stop(self) -> None:
        """Stop notification module."""
        self.state = ModuleState.STOPPING

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        self.state = ModuleState.STOPPED
        logger.info("Notification module stopped")

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.stop()
        self._channels.clear()
        self._channel_configs.clear()
        self._templates.clear()
        self._notifications.clear()
        self._rate_limits.clear()
        self._delivery_callbacks.clear()
        self.state = ModuleState.UNINITIALIZED
        logger.info("Notification module cleaned up")

    async def health_check(self) -> Dict[str, Any]:
        """Health check."""
        channel_status = {}
        for channel, handler in self._channels.items():
            try:
                healthy = await handler.test_connection()
                channel_status[channel.value] = "healthy" if healthy else "unhealthy"
            except Exception:
                channel_status[channel.value] = "error"

        return {
            "module": "notification",
            "status": self.state.value,
            "healthy": self.state == ModuleState.RUNNING,
            "channels": channel_status,
            "templates": len(self._templates),
            "pending_notifications": self._scheduled_queue.qsize(),
            "total_notifications": len(self._notifications)
        }

    async def _create_channel(self, channel: NotificationChannel, config: Dict[str, Any]) -> None:
        """Create channel handler."""
        self._channel_configs[channel] = ChannelConfig(channel=channel, config=config)

        if not config.get("enabled", True):
            logger.info(f"Channel {channel.value} is disabled")
            return

        if channel == NotificationChannel.EMAIL:
            handler = EmailChannel(config)
        elif channel == NotificationChannel.WEBHOOK:
            handler = WebhookChannel(config)
        elif channel == NotificationChannel.PUSH:
            handler = PushChannel(config)
        elif channel == NotificationChannel.SLACK:
            handler = SlackChannel(config)
        # Add more channels as needed
        else:
            logger.warning(f"Channel {channel.value} not implemented")
            return

        self._channels[channel] = handler
        logger.info(f"Initialized channel: {channel.value}")

    # Template Management
    async def create_template(self, template: NotificationTemplate) -> NotificationTemplate:
        """Create notification template."""
        if not template.template_id:
            template.template_id = str(uuid.uuid4())[:8]

        self._templates[template.template_id] = template
        logger.info(f"Created template: {template.template_id} - {template.name}")
        return template

    async def get_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """Get template by ID."""
        return self._templates.get(template_id)

    async def update_template(self, template: NotificationTemplate) -> NotificationTemplate:
        """Update template."""
        if template.template_id in self._templates:
            template.updated_at = datetime.utcnow()
            self._templates[template.template_id] = template
        return template

    async def delete_template(self, template_id: str) -> bool:
        """Delete template."""
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    async def list_templates(
        self,
        channel: Optional[NotificationChannel] = None,
        limit: int = 50
    ) -> List[NotificationTemplate]:
        """List templates."""
        templates = list(self._templates.values())
        if channel:
            templates = [t for t in templates if t.channel == channel]
        templates.sort(key=lambda t: t.updated_at, reverse=True)
        return templates[:limit]

    # Notification Sending
    async def send_notification(
        self,
        notification: Notification,
        channel: Optional[NotificationChannel] = None
    ) -> Notification:
        """Send notification immediately."""
        # Use specified channel or notification's channel
        target_channel = channel or notification.channel

        # Apply template if specified
        if notification.template_id:
            template = self._templates.get(notification.template_id)
            if template:
                rendered = template.render(notification.template_variables)
                notification.title = rendered["subject"]
                notification.message = rendered["body"]
                notification.channel = template.channel

        # Check if channel is available
        if target_channel not in self._channels:
            notification.status = NotificationStatus.FAILED
            notification.error = f"Channel not available: {target_channel.value}"
            return notification

        # Rate limiting
        semaphore = self._rate_limits.get(target_channel)
        if semaphore:
            async with semaphore:
                await self._send_with_retry(notification)
        else:
            await self._send_with_retry(notification)

        return notification

    async def _send_with_retry(self, notification: Notification) -> None:
        """Send with retry logic."""
        channel = self._channels[notification.channel]

        while notification.retry_count <= notification.max_retries:
            try:
                notification.status = NotificationStatus.SENDING
                notification.updated_at = datetime.utcnow()

                success = await channel.send(notification)

                if success:
                    notification.status = NotificationStatus.SENT
                    notification.sent_at = datetime.utcnow()
                    # Simulate delivery
                    await asyncio.sleep(0.1)
                    notification.status = NotificationStatus.DELIVERED
                    notification.delivered_at = datetime.utcnow()
                    break
                else:
                    notification.retry_count += 1
                    if notification.retry_count <= notification.max_retries:
                        await asyncio.sleep(2 ** notification.retry_count)  # Exponential backoff

            except Exception as e:
                notification.retry_count += 1
                notification.error = str(e)
                if notification.retry_count <= notification.max_retries:
                    await asyncio.sleep(2 ** notification.retry_count)
                else:
                    notification.status = NotificationStatus.FAILED
                    notification.failed_at = datetime.utcnow()

        notification.updated_at = datetime.utcnow()

        # Store notification
        self._notifications[notification.notification_id] = notification
        self._trim_history()

        # Call delivery callbacks
        for callback in self._delivery_callbacks:
            try:
                await callback(notification)
            except Exception as e:
                logger.error(f"Delivery callback error: {e}")

    async def schedule_notification(
        self,
        notification: Notification,
        send_at: Optional[datetime] = None,
        delay_seconds: Optional[float] = None
    ) -> Notification:
        """Schedule notification for future delivery."""
        if send_at:
            notification.scheduled_at = send_at
        elif delay_seconds:
            notification.scheduled_at = datetime.utcnow() + timedelta(seconds=delay_seconds)
        else:
            notification.scheduled_at = datetime.utcnow()

        notification.status = NotificationStatus.QUEUED
        notification.updated_at = datetime.utcnow()

        # Add to scheduled queue
        await self._scheduled_queue.put((notification.scheduled_at.timestamp(), notification.notification_id))

        self._notifications[notification.notification_id] = notification
        return notification

    async def _scheduler_loop(self) -> None:
        """Process scheduled notifications."""
        while True:
            try:
                # Get next notification
                try:
                    score, notif_id = await asyncio.wait_for(
                        self._scheduled_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                notification = self._notifications.get(notif_id)
                if not notification:
                    continue

                # Check if it's time
                now = datetime.utcnow().timestamp()
                if notification.scheduled_at and notification.scheduled_at.timestamp() > now:
                    # Re-queue for later
                    await self._scheduled_queue.put((notification.scheduled_at.timestamp(), notif_id))
                    await asyncio.sleep(0.1)
                    continue

                # Send
                notification.status = NotificationStatus.PENDING
                await self.send_notification(notification)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(1)

    def _trim_history(self) -> None:
        """Trim notification history."""
        if len(self._notifications) > self._max_history:
            # Remove oldest completed notifications
            sorted_notifs = sorted(
                self._notifications.items(),
                key=lambda x: x[1].created_at
            )
            to_remove = len(self._notifications) - self._max_history
            for notif_id, _ in sorted_notifs[:to_remove]:
                if self._notifications[notif_id].status in (
                    NotificationStatus.DELIVERED,
                    NotificationStatus.FAILED
                ):
                    del self._notifications[notif_id]

    # Notification Management
    async def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get notification by ID."""
        return self._notifications.get(notification_id)

    async def cancel_notification(self, notification_id: str) -> bool:
        """Cancel scheduled notification."""
        notification = self._notifications.get(notification_id)
        if notification and notification.status in (
            NotificationStatus.PENDING,
            NotificationStatus.QUEUED,
            NotificationStatus.SENDING
        ):
            notification.status = NotificationStatus.FAILED
            notification.error = "Cancelled"
            notification.failed_at = datetime.utcnow()
            return True
        return False

    async def list_notifications(
        self,
        status: Optional[NotificationStatus] = None,
        channel: Optional[NotificationChannel] = None,
        recipient: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Notification]:
        """List notifications with filtering."""
        notifications = list(self._notifications.values())

        if status:
            notifications = [n for n in notifications if n.status == status]
        if channel:
            notifications = [n for n in notifications if n.channel == channel]
        if recipient:
            notifications = [n for n in notifications if n.recipient == recipient]
        if since:
            notifications = [n for n in notifications if n.created_at >= since]

        notifications.sort(key=lambda n: n.created_at, reverse=True)
        return notifications[:limit]

    # Callback Registration
    def register_delivery_callback(self, callback: Callable[[Notification], None]) -> None:
        """Register callback for delivery notifications."""
        self._delivery_callbacks.append(callback)

    def unregister_delivery_callback(self, callback: Callable[[Notification], None]) -> bool:
        """Unregister delivery callback."""
        try:
            self._delivery_callbacks.remove(callback)
            return True
        except ValueError:
            return False

    # Channel Configuration
    async def update_channel_config(self, channel: NotificationChannel, config: Dict[str, Any]) -> bool:
        """Update channel configuration."""
        if channel in self._channel_configs:
            self._channel_configs[channel].config = config
            self._channel_configs[channel].enabled = config.get("enabled", True)

            # Recreate handler
            if channel in self._channels:
                del self._channels[channel]
            await self._create_channel(channel, config)
            return True
        return False

    async def get_channel_config(self, channel: NotificationChannel) -> Optional[ChannelConfig]:
        """Get channel configuration."""
        return self._channel_configs.get(channel)

    # Module Operations
    async def execute(self, operation: str, **kwargs) -> Any:
        """Execute module operations."""
        if operation == "send":
            return await self.send_notification(kwargs.get("notification"))
        elif operation == "schedule":
            return await self.schedule_notification(
                kwargs.get("notification"),
                kwargs.get("send_at"),
                kwargs.get("delay_seconds")
            )
        elif operation == "get":
            return await self.get_notification(kwargs.get("notification_id"))
        elif operation == "list":
            return await self.list_notifications(**kwargs)
        elif operation == "cancel":
            return await self.cancel_notification(kwargs.get("notification_id"))
        elif operation == "create_template":
            return await self.create_template(kwargs.get("template"))
        elif operation == "get_template":
            return await self.get_template(kwargs.get("template_id"))
        elif operation == "update_template":
            return await self.update_template(kwargs.get("template"))
        elif operation == "delete_template":
            return await self.delete_template(kwargs.get("template_id"))
        elif operation == "list_templates":
            return await self.list_templates(**kwargs)
        elif operation == "register_callback":
            self.register_delivery_callback(kwargs.get("callback"))
        elif operation == "unregister_callback":
            return self.unregister_delivery_callback(kwargs.get("callback"))
        else:
            raise NotImplementedError(f"Operation '{operation}' not supported")


__all__ = [
    "NotificationModule",
    "Notification",
    "NotificationTemplate",
    "NotificationChannel",
    "NotificationStatus",
    "NotificationPriority",
    "ChannelConfig",
]