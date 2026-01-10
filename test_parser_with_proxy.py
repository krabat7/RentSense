import sys
sys.path.insert(0, '.')

from app.parser.main import getResponse, prePage
from app.parser.pagecheck import pagecheck

test_id = sys.argv[1] if len(sys.argv) > 1 else "311739319"

print(f"Testing parser with proxy for offer {test_id}...")
print("=" * 50)

response = getResponse(test_id, type=1, dbinsert=False)
if not response:
    print("ERROR: No response received")
    sys.exit(1)

print(f"Response received, length: {len(response)} characters")

if "Captcha" in response or "captcha" in response.lower():
    print("WARNING: Captcha detected in response!")
    with open(f'cian_proxy_test_{test_id}.html', 'w', encoding='utf-8') as f:
        f.write(response)
    print(f"Saved response to cian_proxy_test_{test_id}.html")
else:
    print("No captcha detected!")
    
    pageJS = prePage(response, type=1)
    if pageJS:
        print(f"OK Found pageJS! Keys: {list(pageJS.keys())[:10]}")
        
        if data := pagecheck(pageJS):
            print(f"OK Successfully parsed data!")
            print(f"  Offer ID: {data.get('offers', {}).get('cian_id')}")
            print(f"  Price: {data.get('offers', {}).get('price')}")
            print(f"  Rooms: {data.get('realty_inside', {}).get('rooms_count')}")
            print(f"  Address: {data.get('addresses', {}).get('address')}")
        else:
            print("FAILED Failed to parse data from pageJS")
    else:
        print("FAILED No pageJS found - checking for offerData...")
        if '"offerData":' in response:
            print("  Found 'offerData' in response!")
        else:
            print("  'offerData' not found in response")

