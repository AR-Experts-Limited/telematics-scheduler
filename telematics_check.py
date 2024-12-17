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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.chrome.webdriver import Options

# Set your credentials
URL = "https://telematics.arexperts.co.uk/"
USERNAME = "outofhours@gmail.com"
PASSWORD = "OutOfHours123"

# Email Configuration
SENDER_EMAIL = "artestingdriver@gmail.com"
SENDER_PASSWORD = "chic kqpw ekxm kzyo"
RECIPIENT_EMAIL = "joeteo1999@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Initialize Chrome options
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--headless")  # Ensure it runs in headless mode on CI/CD environments
options.add_argument("--no-sandbox")  # Required for running Chrome in Linux containers
options.add_argument("--disable-dev-shm-usage")  # Prevents shared memory issues
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")

# Initialize the Chrome driver
driver = webdriver.Chrome(options=options)

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
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(attachment_path)}')
                msg.attach(part)

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
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file.write(f"Log Time: {current_time}\n")
        file.write(f"Login Status: {status}\n\n")
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
        failure_message = driver.find_element(By.CLASS_NAME, "error-message")
        return failure_message.is_displayed()
    except NoSuchElementException:
        return False

def check_telematics_site(url, username, password):
    try:
        driver.get(url)

        # Wait for fields to load
        username_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "email")))
        password_input = driver.find_element(By.NAME, "password")
        login_button = driver.find_element(By.CLASS_NAME, "Login_btn__CSBJW")

        # Debug: Check for hidden fields
        hidden_inputs = driver.find_elements(By.TAG_NAME, "input")
        for field in hidden_inputs:
            if field.get_attribute("type") == "hidden":
                print(f"Hidden field: Name={field.get_attribute('name')}, Value={field.get_attribute('value')}")

        # Enter credentials and submit
        username_input.send_keys(username)
        password_input.send_keys(password)
        driver.execute_script("arguments[0].click();", login_button)  # JavaScript click

        # Wait for response
        time.sleep(5)
        browser_logs = driver.get_log("browser")
        login_failed = check_login_failure() or check_console_for_errors(browser_logs)
        user_data_found = any("User Data" in log["message"] for log in browser_logs)

        # Determine login status
        login_status = "SUCCESS" if user_data_found else "FAILURE"
        print(f"Login Status: {login_status}")

        # Save logs and take a screenshot
        logs_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = os.path.join(logs_dir, f"console_logs_{timestamp}.txt")
        screenshot_path = os.path.join(logs_dir, f"login_failure_{timestamp}.png")
        save_logs_to_file(browser_logs, login_status, log_file)

        if login_status == "FAILURE":
            driver.save_screenshot(screenshot_path)
            print(f"Screenshot saved at: {screenshot_path}")
            send_email(
                "ALERT: Telematics Login Failed",
                f"Login attempt failed.\n\nTimestamp: {timestamp}\nLogs: {log_file}\nScreenshot: {screenshot_path}",
                log_file
            )
        else:
            print("Login Successful.")

    except WebDriverException as e:
        print(f"Website failed to load: {e}")
        send_email("ALERT: Website Not Loading", f"Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
        send_email("ALERT: Error Occurred During Login Check", f"Error: {e}")
    finally:
        driver.quit()

# Execute the function
check_telematics_site(URL, USERNAME, PASSWORD)
