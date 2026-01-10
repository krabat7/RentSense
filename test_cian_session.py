import requests
import sys
import time

test_id = sys.argv[1] if len(sys.argv) > 1 else "311739319"

session = requests.Session()

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}

print("Step 1: Getting main page to get cookies...")
main_page = session.get("https://www.cian.ru", headers=headers, timeout=10)
print(f"Main page status: {main_page.status_code}")
print(f"Cookies: {session.cookies.get_dict()}")

time.sleep(2)

print(f"\nStep 2: Getting offer page {test_id}...")
url = f"https://www.cian.ru/rent/flat/{test_id}/"
response = session.get(url, headers=headers, timeout=10)

print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type')}")

if "Captcha" in response.text or "captcha" in response.text.lower():
    print("CAPTCHA detected!")
    with open(f'cian_captcha_{test_id}.html', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print(f"Saved to cian_captcha_{test_id}.html")
else:
    print("No captcha! Checking for data...")
    if '"offerData":' in response.text:
        print("Found offerData!")
    elif 'offer' in response.text.lower():
        print("Found 'offer' keyword")
    else:
        print("No offer data found")
        with open(f'cian_page_{test_id}.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"Saved to cian_page_{test_id}.html")

