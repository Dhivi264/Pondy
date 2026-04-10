import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from app.config import settings
import threading

logger = logging.getLogger(__name__)

class AlertSender:
    def __init__(self):
        self.smtp_host = getattr(settings, "SMTP_HOST", "")
        self.smtp_port = getattr(settings, "SMTP_PORT", 587)
        self.smtp_user = getattr(settings, "SMTP_USER", "")
        self.smtp_pass = getattr(settings, "SMTP_PASS", "")
        self.admin_email = getattr(settings, "ADMIN_EMAIL", "")

    def send_critical_alert(self, subject: str, message: str):
        if not self.smtp_host or not self.admin_email:
            logger.info(f"[AlertSender] Email not configured. Skipping alert: {subject}")
            return
            
        def _send():
            try:
                msg = MIMEMultipart()
                msg['From'] = self.smtp_user
                msg['To'] = self.admin_email
                msg['Subject'] = f"[Smart CCTV Alert] {subject}"
                
                body = f"CRITICAL SYSTEM ALERT\n\n{message}\n\nPlease check the dashboard immediately."
                msg.attach(MIMEText(body, 'plain'))
                
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
                if self.smtp_user and self.smtp_pass:
                    server.login(self.smtp_user, self.smtp_pass)
                text = msg.as_string()
                server.sendmail(self.smtp_user, self.admin_email, text)
                server.quit()
                logger.info(f"[AlertSender] Successfully sent alert to {self.admin_email}")
            except Exception as e:
                logger.error(f"[AlertSender] Failed to send email alert: {e}")

        # Send asynchronously so it doesn't block the AI Watchdog
        threading.Thread(target=_send, daemon=True).start()

alert_sender = AlertSender()
