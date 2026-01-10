import sys
sys.path.insert(0, '.')

from app.parser.main import getResponse, prePage
import json

test_id = "311739319"

print("Getting rent offer data...")
response = getResponse(test_id, type=1, dbinsert=False)
if not response:
    print("No response")
    sys.exit(1)

pageJS = prePage(response, type=1)
if not pageJS or 'offer' not in pageJS:
    print("No offer in pageJS")
    sys.exit(1)

offer = pageJS['offer']

print("=" * 70)
print("FULL OFFER STRUCTURE FOR RENT")
print("=" * 70)

def print_structure(obj, prefix="", max_depth=3, current_depth=0):
    if current_depth >= max_depth:
        return
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                print(f"{prefix}{key}: {type(value).__name__}")
                if isinstance(value, dict) and len(value) > 0:
                    print_structure(value, prefix + "  ", max_depth, current_depth + 1)
                elif isinstance(value, list) and len(value) > 0 and len(value) <= 5:
                    if isinstance(value[0], dict):
                        print(f"{prefix}  [0]: dict with keys: {list(value[0].keys())[:10]}")
            else:
                print(f"{prefix}{key}: {value}")

print("\nTop-level keys in offer:")
print_structure(offer, max_depth=2)

print("\n" + "=" * 70)
print("KEY FIELDS FOR RENT:")
print("=" * 70)

key_fields = {
    'cianId': offer.get('cianId'),
    'dealType': offer.get('dealType'),
    'priceTotalRur': offer.get('priceTotalRur'),
    'bargainTerms': offer.get('bargainTerms'),
    'roomsCount': offer.get('roomsCount'),
    'totalArea': offer.get('totalArea'),
    'livingArea': offer.get('livingArea'),
    'kitchenArea': offer.get('kitchenArea'),
    'floorNumber': offer.get('floorNumber'),
    'category': offer.get('category'),
    'publicationDate': offer.get('publicationDate'),
    'description': offer.get('description'),
    'photos': len(offer.get('photos', [])) if offer.get('photos') else None,
    'geo': offer.get('geo'),
    'building': offer.get('building'),
    'newbuilding': offer.get('newbuilding'),
    'company': offer.get('company'),
    'agent': offer.get('agent'),
}

for key, value in key_fields.items():
    if value is not None:
        if isinstance(value, dict):
            print(f"{key}: dict with keys: {list(value.keys())[:15]}")
        elif isinstance(value, list):
            print(f"{key}: list with {len(value)} items")
        else:
            print(f"{key}: {value}")

print("\n" + "=" * 70)
print("BARGAIN TERMS (RENT SPECIFIC):")
print("=" * 70)
if offer.get('bargainTerms'):
    bt = offer['bargainTerms']
    for key, value in bt.items():
        print(f"  {key}: {value}")

print("\n" + "=" * 70)
print("GEO DATA:")
print("=" * 70)
if offer.get('geo'):
    geo = offer['geo']
    print(f"  coordinates: {geo.get('coordinates')}")
    print(f"  address: {geo.get('address')}")
    if geo.get('undergrounds'):
        print(f"  undergrounds: {len(geo.get('undergrounds'))} items")
        for i, ug in enumerate(geo.get('undergrounds', [])[:3]):
            print(f"    [{i}]: {ug}")

print("\n" + "=" * 70)
print("BUILDING DATA:")
print("=" * 70)
if offer.get('building'):
    building = offer['building']
    for key, value in building.items():
        if not isinstance(value, (dict, list)):
            print(f"  {key}: {value}")

print("\n" + "=" * 70)
print("SAVING FULL JSON FOR ANALYSIS:")
print("=" * 70)
with open('rent_offer_full.json', 'w', encoding='utf-8') as f:
    json.dump(offer, f, ensure_ascii=False, indent=2)
print("Saved to rent_offer_full.json")

