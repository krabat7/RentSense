import sys
sys.path.insert(0, '.')

from app.parser.main import getResponse, prePage
from app.parser.pagecheck import pagecheck

test_id = sys.argv[1] if len(sys.argv) > 1 else "311739319"

response = getResponse(test_id, type=1, dbinsert=False)
if not response:
    print("No response")
    sys.exit(1)

pageJS = prePage(response, type=1)
if not pageJS:
    print("No pageJS")
    sys.exit(1)

print("pageJS keys:", list(pageJS.keys()))
if 'offer' in pageJS:
    offer = pageJS['offer']
    print("\nOffer keys:", list(offer.keys())[:20])
    print(f"cianId: {offer.get('cianId')}")
    print(f"priceTotalRur: {offer.get('priceTotalRur')}")
    print(f"dealType: {offer.get('dealType')}")
    print(f"trackingData: {offer.get('trackingData')}")
    
    if offer.get('trackingData', {}).get('oblId') != 1:
        print(f"\nWARNING: oblId = {offer.get('trackingData', {}).get('oblId')}, expected 1")
    
    if not offer.get('cianId') or not offer.get('priceTotalRur'):
        print(f"\nWARNING: Missing required fields")
        print(f"  cianId: {offer.get('cianId')}")
        print(f"  priceTotalRur: {offer.get('priceTotalRur')}")

data = pagecheck(pageJS)
if data:
    print("\nSUCCESS: Data parsed!")
else:
    print("\nFAILED: pagecheck returned None")

