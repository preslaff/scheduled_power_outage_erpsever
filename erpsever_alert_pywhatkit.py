import pywhatkit as kit
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import schedule

def setup_driver():
    # Set up the Chrome driver using WebDriverManager
    driver_path = ChromeDriverManager().install()
    service = Service(driver_path)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def check_element_presence(driver, css_selector, description):
    element = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))
    print(f"{description} found: {element.tag_name}")
    return element

def send_whatsapp_message(text, recipient_number):
    try:
        # Send a WhatsApp message using pywhatkit
        kit.sendwhatmsg_instantly(recipient_number, text)
        print(f"WhatsApp message sent to {recipient_number}")
    except Exception as e:
        print(f"Failed to send WhatsApp message: {e}")

def check_interruptions(driver, municipality, target_text, recipient_number):
    try:
        url = 'https://www.energo-pro.bg/bg/planirani-prekysvanija'
        driver.get(url)

        # Wait and check for each element in the hierarchy
        check_element_presence(driver, 'div.map-interruptions', 'Map Interruptions div')
        time.sleep(2)  # Give additional time for dynamic content to load

        check_element_presence(driver, 'body > div.table.site-table', 'Main table div')
        check_element_presence(driver, 'body > div.table.site-table > main', 'Main tag')
        check_element_presence(driver, 'body > div.table.site-table > main > section:nth-of-type(2)', 'Second section')
        check_element_presence(driver, 'body > div.table.site-table > main > section:nth-of-type(2) > div.wrapper', 'Wrapper div')

        # # Output the current page source for debugging
        # page_source = driver.page_source
        # with open("page_source.html", "w", encoding="utf-8") as file:
        #     file.write(page_source)

        # Check for the modal overlay and close it if it exists
        try:
            modal_overlay = driver.find_element(By.CSS_SELECTOR, 'div.modal-overlay')
            if modal_overlay.is_displayed():
                print("Modal overlay detected. Attempting to close.")
                driver.execute_script("arguments[0].click();", modal_overlay)
                time.sleep(2)  # Give some time for the modal to close
        except Exception as e:
            print(f"No modal overlay found or error occurred: {e}")

        # Find and click the desired municipality
        area_items = driver.find_elements(By.CSS_SELECTOR, 'div.map-interruptions > div.sidebar > div.areas > div.item')

        clicked = False
        for item in area_items:
            area = item.find_element(By.TAG_NAME, 'strong').text
            if area == municipality:
                print(f"Found and clicking on municipality: {area}")
                driver.execute_script("arguments[0].click();", item)
                clicked = True
                break

        if not clicked:
            print(f"Municipality '{municipality}' not found.")
            return

        # Wait for the interruption data to load
        time.sleep(5)  # Wait for the page to load the interruptions

        # Increase the wait time and add a retry mechanism for waiting for the interruption data
        wait = WebDriverWait(driver, 30)
        for attempt in range(3):
            try:
                wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'body > div.table.site-table > main > section:nth-of-type(2) div.wrapper div.interruption-data ul#interruption_areas li[data-interruption="for_next_48_hours"]')
                ))
                print(f"Attempt {attempt + 1}: Found the interruption data.")  # Debug statement
                break
            except Exception as e:
                print(f"Attempt {attempt + 1}: Failed to find the interruption data: {e}")
                time.sleep(5)  # Wait before retrying

        # Retrieve the interruption data
        interruptions = driver.find_elements(
            By.CSS_SELECTOR, 'body > div.table.site-table > main > section:nth-of-type(2) div.wrapper div.interruption-data ul#interruption_areas li[data-interruption="for_next_48_hours"]'
        )
        
        print(f"Found {len(interruptions)} interruption entries.")  # Debug statement
        
        for interruption in interruptions:
            interruption_text = interruption.find_element(By.CSS_SELECTOR, 'div.text').text.strip()
            interruption_period = interruption.find_element(By.CSS_SELECTOR, 'div.period').text.strip()
            if target_text in interruption_text:
                print(f"Match found for {target_text}!")
                message_text = f"Period: {interruption_period}\nDetails: {interruption_text}"
                send_whatsapp_message(message_text, recipient_number)
                return
        
        print(f"No matches found for {target_text}.")  # Debug statement

    finally:
        driver.quit()

def job(municipality, target_text, recipient_number):
    driver = setup_driver()
    check_interruptions(driver, municipality, target_text, recipient_number)

if __name__ == "__main__":
    municipality = input("Въведете област (Варна, Велико Търново, Габрово, Добрич, Разград, Русе, Силистра Търговище, Шумен): ")
    target_text = input("Въведете място (улица, име на село или име на бизнес абонат ): ")
    recipient_number = input("Въведете Whatsapp номер (във формат +359456557890): ")

    # Schedule the job to run every hour
    schedule.every().hour.do(job, municipality, target_text, recipient_number)

    print("Service started...")

    while True:
        schedule.run_pending()
        time.sleep(1)
