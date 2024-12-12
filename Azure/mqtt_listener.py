import smtplib
from email.mime.text import MIMEText

# SMTP Configuration
SMTP_SERVER = "172.166.233.123"
SMTP_PORT = 587  # Use 587 for TLS
SMTP_USERNAME = "test@detbedsteintranet.online"
SMTP_PASSWORD = "A987zureuser."

# Email Details
EMAIL_FROM = "test@detbedsteintranet.online"
EMAIL_TO = "test@detbedsteintranet.online"

EMAIL_BODY = """
Hello,

This is a critical MQTT alert. Please check your MQTT services immediately.

Best regards,
Your Monitoring System
"""

def send_email(cpr="010101-1111"):
    EMAIL_SUBJECT = f"Critical MQTT Alert {cpr}"
    msg = MIMEText(EMAIL_BODY)
    msg['Subject'] = EMAIL_SUBJECT
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.set_debuglevel(0)  # Enable debug output
            server.ehlo()
            server.starttls()  # Upgrade the connection to secure
            server.ehlo()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    send_email("010101-1111")
