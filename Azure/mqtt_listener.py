import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# SMTP Configuration
SMTP_SERVER = "172.166.233.123"
SMTP_PORT = 587  # Use 587 for TLS
SMTP_USERNAME = "test@detbedsteintranet.online"
SMTP_PASSWORD = "A987zureuser."

# Email Details
EMAIL_FROM = "test@detbedsteintranet.online"
EMAIL_TO = "test@detbedsteintranet.online"
EMAIL_SUBJECT = "Critical MQTT Alert"

def send_email():
    # Get the current time formatted as YYYY-MM-DD HH:MM:SS
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create the email body with the current time included
    email_body = f"""
Hello,

This is a critical MQTT alert sent at {current_time}. Please check your MQTT services immediately.

Best regards,
Your Monitoring System
"""

    # Create a MIMEText object to represent the email
    msg = MIMEText(email_body)
    msg['Subject'] = EMAIL_SUBJECT
    msg['From'] = EMAIL_FROM
    msg['To'] = EMAIL_TO

    try:
        # Establish a connection to the SMTP server
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.set_debuglevel(0)  # Set to 1 to enable debug output
            server.ehlo()
            server.starttls()  # Upgrade the connection to secure
            server.ehlo()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    send_email()
