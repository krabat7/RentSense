import sys
sys.path.insert(0, '.')

from app.parser.main import getResponse, prePage
from app.parser.pagecheck import pagecheck

test_id = sys.argv[1] if len(sys.argv) > 1 else "311739319"

print(f"Full parse test for {test_id}...")
print("=" * 50)

response = getResponse(test_id, type=1, dbinsert=False)
if not response:
    print("ERROR: No response")
    sys.exit(1)

print(f"Response length: {len(response)}")
print(f"Has offerData: {'offerData' in response}")

pageJS = prePage(response, type=1)
if not pageJS:
    print("ERROR: No pageJS found")
    sys.exit(1)

print(f"pageJS found! Keys: {list(pageJS.keys())[:10]}")

data = pagecheck(pageJS)
if not data:
    print("ERROR: Failed to parse data")
    sys.exit(1)

print("SUCCESS: Data parsed!")
print(f"  Offer ID: {data.get('offers', {}).get('cian_id')}")
print(f"  Price: {data.get('offers', {}).get('price')}")
print(f"  Rooms: {data.get('realty_inside', {}).get('rooms_count')}")
print(f"  Area: {data.get('realty_inside', {}).get('total_area')}")

