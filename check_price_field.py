import sys
sys.path.insert(0, '.')

from app.parser.main import getResponse, prePage
import json

test_id = "311739319"

response = getResponse(test_id, type=1, dbinsert=False)
if not response:
    print("No response")
    sys.exit(1)

pageJS = prePage(response, type=1)
if not pageJS or 'offer' not in pageJS:
    print("No offer in pageJS")
    sys.exit(1)

offer = pageJS['offer']

print("Searching for price fields...")
print(f"priceTotalRur: {offer.get('priceTotalRur')}")
print(f"price: {offer.get('price')}")
print(f"bargainTerms: {offer.get('bargainTerms')}")

if 'bargainTerms' in offer:
    bt = offer['bargainTerms']
    print(f"\nbargainTerms keys: {list(bt.keys()) if isinstance(bt, dict) else 'not a dict'}")
    if isinstance(bt, dict):
        print(f"bargainTerms price: {bt.get('price')}")
        print(f"bargainTerms priceRur: {bt.get('priceRur')}")

print("\nAll offer keys containing 'price':")
for key in offer.keys():
    if 'price' in key.lower():
        print(f"  {key}: {offer.get(key)}")

