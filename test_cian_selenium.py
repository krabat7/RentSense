from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import sys
import time
import json
import re

test_id = sys.argv[1] if len(sys.argv) > 1 else "311739319"

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

print("Initializing Chrome driver...")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    url = f"https://www.cian.ru/rent/flat/{test_id}/"
    print(f"Loading page: {url}")
    driver.get(url)
    
    time.sleep(5)
    
    page_source = driver.page_source
    
    if "Captcha" in page_source or "captcha" in page_source.lower():
        print("CAPTCHA detected even with Selenium!")
        with open(f'cian_selenium_captcha_{test_id}.html', 'w', encoding='utf-8') as f:
            f.write(page_source)
        print(f"Saved to cian_selenium_captcha_{test_id}.html")
    else:
        print("No captcha! Checking for data...")
        if '"offerData":' in page_source:
            print("Found offerData!")
            match = re.search(r'"offerData":\s*(\{.*?\})', page_source, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    print(f"Parsed JSON! Keys: {list(data.keys())[:10]}")
                except:
                    print("Failed to parse JSON")
        elif 'offer' in page_source.lower():
            print("Found 'offer' keyword")
        else:
            print("No offer data found")
            with open(f'cian_selenium_{test_id}.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            print(f"Saved to cian_selenium_{test_id}.html")
            
finally:
    driver.quit()
    print("Driver closed")

