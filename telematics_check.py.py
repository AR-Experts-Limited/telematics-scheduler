import time
import datetime
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException

# Set your credentials
URL = "https://telematics.arexperts.co.uk/"
USERNAME = "outofhours@gmail.com"
PASSWORD = "OutOfHours12"

# Email Configuration
SENDER_EMAIL = "artestingdriver@gmail.com"
SENDER_PASSWORD = "chic kqpw ekxm kzyo"
RECIPIENT_EMAIL = "telematics@arexperts.co.uk"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Path to ChromeDriver
driver_path = r"E:\AR\chromedriver-win64\chromedriver-win64\chromedriver.exe"

# Initialize Selenium browser
options = Options()
options.add_argument("--start-maximized")
options.set_capability("goog:loggingPrefs", {"browser": "ALL"})  # Enable browser logs
service = Service(driver_path)
driver = webdriver.Chrome(service=service, options=options)

def send_email(subject, body, attachment_path=None):
    """Send an email with the given subject, body, and optional attachment."""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))

        # Attach file if provided
        if attachment_path and os.path.exists(attachment_path):
            attachment = open(attachment_path, "rb")
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
            msg.attach(part)
            attachment.close()

        # Connect to SMTP server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)

        server.send_message(msg)
        server.quit()
        print("Email sent successfully with logs.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def save_logs_to_file(logs, status, filename):
    """Save login status and browser logs to a text file with formatted timestamps."""
    with open(filename, "w", encoding="utf-8") as file:
        # Write the login status with a proper timestamp
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file.write(f"Log Time: {current_time}\n")
        file.write(f"Login Status: {status}\n\n")

        # Write console logs with readable timestamps
        file.write("Console Logs:\n")
        for log in logs:
            readable_time = datetime.datetime.fromtimestamp(log['timestamp'] / 1000).strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"{readable_time} - {log['message']}\n")

def check_console_for_errors(browser_logs):
    """Check console logs for 400 errors or User Data: undefined."""
    for log in browser_logs:
        if "400" in log["message"] or "User Data: undefined" in log["message"]:
            return True
    return False

def check_login_failure():
    """Check for login failure message on the page."""
    try:
        failure_message = driver.find_element(By.CLASS_NAME, "error-message")  # Replace with actual class or element
        if failure_message.is_displayed():
            return True
    except NoSuchElementException:
        return False
    return False

def check_telematics_site(url, username, password):
    try:
        driver.get(url)
        time.sleep(2)  # Allow page to load

        # Locate username, password fields, and login button
        username_input = driver.find_element(By.NAME, "email")
        password_input = driver.find_element(By.NAME, "password")
        login_button = driver.find_element(By.CLASS_NAME, "Login_btn__CSBJW")

        # Enter credentials
        username_input.send_keys(username)
        password_input.send_keys(password)
        login_button.click()

        time.sleep(5)  # Wait for login processing

        # Capture browser console logs
        browser_logs = driver.get_log("browser")

        # Check for login failure on page or in console logs
        login_failed = check_login_failure() or check_console_for_errors(browser_logs)
        user_data_found = any("User Data" in log["message"] for log in browser_logs)

        # Determine login status
        if login_failed:
            login_status = "FAILURE"
        else:
            login_status = "SUCCESS" if user_data_found else "FAILURE"

        print(f"Login Status: {login_status}")

        # Generate a timestamped filename
        logs_dir = r"E:\AR\logs"
        os.makedirs(logs_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(logs_dir, f"console_logs_{timestamp}.txt")

        # Save logs and status to a file
        save_logs_to_file(browser_logs, login_status, filename)
        print(f"Console logs saved to: {filename}")

        # Send email if login fails
        if login_status == "FAILURE":
            email_subject = "ALERT: Telematics Login Failed"
            email_body = (f"Telematics login attempt failed.\n\n"
                          f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                          f"Logs saved at: {filename}")
            send_email(email_subject, email_body, filename)

    except WebDriverException as e:
        print(f"Website failed to load: {e}")
        email_subject = "ALERT: Website Not Loading"
        email_body = (f"The website '{url}' failed to load due to the following error:\n\n{e}\n\n"
                      f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        send_email(email_subject, email_body)
    except Exception as e:
        print(f"An error occurred: {e}")
        email_subject = "ALERT: Error Occurred During Login Check"
        email_body = f"An error occurred while trying to check the telematics site:\n\n{e}"
        send_email(email_subject, email_body)
    finally:
        driver.quit()

# Execute the function
check_telematics_site(URL, USERNAME, PASSWORD)
