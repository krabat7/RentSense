import json

with open('rent_offer_full.json', 'r', encoding='utf-8') as f:
    offer = json.load(f)

print("=" * 70)
print("ANALYZING RENT OFFER STRUCTURE")
print("=" * 70)

print("\n1. BASIC FIELDS:")
basic_fields = ['cianId', 'dealType', 'category', 'publicationDate', 'description']
for field in basic_fields:
    value = offer.get(field)
    print(f"  {field}: {value}")

print("\n2. PRICE FIELDS (RENT SPECIFIC):")
print(f"  priceTotalRur: {offer.get('priceTotalRur')}")
if offer.get('bargainTerms'):
    bt = offer['bargainTerms']
    print(f"  bargainTerms.price: {bt.get('price')}")
    print(f"  bargainTerms.paymentPeriod: {bt.get('paymentPeriod')}")
    print(f"  bargainTerms.leaseTermType: {bt.get('leaseTermType')}")
    print(f"  bargainTerms.deposit: {bt.get('deposit')}")
    print(f"  bargainTerms.prepayMonths: {bt.get('prepayMonths')}")
    print(f"  bargainTerms.utilitiesTerms: {bt.get('utilitiesTerms')}")
    print(f"  bargainTerms.clientFee: {bt.get('clientFee')}")
    print(f"  bargainTerms.agentFee: {bt.get('agentFee')}")

print("\n3. AREA FIELDS:")
print(f"  totalArea: {offer.get('totalArea')}")
print(f"  livingArea: {offer.get('livingArea')}")
print(f"  kitchenArea: {offer.get('kitchenArea')}")
print(f"  roomsCount: {offer.get('roomsCount')}")

print("\n4. BUILDING FIELDS:")
if offer.get('building'):
    b = offer['building']
    print(f"  floorsCount: {b.get('floorsCount')}")
    print(f"  floorNumber: {offer.get('floorNumber')}")
    print(f"  buildYear: {b.get('buildYear')}")
    print(f"  ceilingHeight: {b.get('ceilingHeight')}")
    print(f"  hasGarbageChute: {b.get('hasGarbageChute')}")
    print(f"  passengerLiftsCount: {b.get('passengerLiftsCount')}")
    print(f"  cargoLiftsCount: {b.get('cargoLiftsCount')}")
    if b.get('parking'):
        print(f"  parking.type: {b.get('parking', {}).get('type')}")

print("\n5. INTERIOR FIELDS:")
print(f"  repairType: {offer.get('repairType')}")
print(f"  balconiesCount: {offer.get('balconiesCount')}")
print(f"  loggiasCount: {offer.get('loggiasCount')}")
print(f"  separateWcsCount: {offer.get('separateWcsCount')}")
print(f"  combinedWcsCount: {offer.get('combinedWcsCount')}")
print(f"  windowsViewType: {offer.get('windowsViewType')}")

print("\n6. GEO FIELDS:")
if offer.get('geo'):
    geo = offer['geo']
    print(f"  coordinates: {geo.get('coordinates')}")
    if geo.get('undergrounds'):
        ug = geo['undergrounds'][0]
        print(f"  metro.name: {ug.get('name')}")
        print(f"  metro.travelType: {ug.get('travelType')}")
        print(f"  metro.travelTime: {ug.get('travelTime')}")
    if geo.get('address'):
        print(f"  address: {len(geo.get('address'))} items")

print("\n7. RENT-SPECIFIC FIELDS (may not be in pagecheck):")
rent_specific = {
    'paymentPeriod': offer.get('bargainTerms', {}).get('paymentPeriod'),
    'leaseTermType': offer.get('bargainTerms', {}).get('leaseTermType'),
    'deposit': offer.get('bargainTerms', {}).get('deposit'),
    'prepayMonths': offer.get('bargainTerms', {}).get('prepayMonths'),
    'utilitiesIncluded': offer.get('bargainTerms', {}).get('utilitiesTerms', {}).get('includedInPrice'),
    'clientFee': offer.get('bargainTerms', {}).get('clientFee'),
    'agentFee': offer.get('bargainTerms', {}).get('agentFee'),
}

for key, value in rent_specific.items():
    if value is not None:
        print(f"  {key}: {value}")

print("\n8. FIELDS THAT MAY BE MISSING IN RENT:")
sale_specific = ['mortgageAllowed', 'saleType']
for field in sale_specific:
    value = offer.get('bargainTerms', {}).get(field)
    print(f"  bargainTerms.{field}: {value} (may be None for rent)")

print("\n" + "=" * 70)
print("COMPARISON WITH PAGECHECK.PY:")
print("=" * 70)

print("\nFields parsed by pagecheck.py:")
parsed_fields = [
    'price', 'photos_count', 'floor_number', 'category', 'publication_at',
    'deal_type', 'flat_type', 'is_duplicate', 'description',
    'rooms_count', 'is_apartment', 'is_penthouse',
    'repair_type', 'balconies', 'loggias', 'separated_wc', 'combined_wc', 'windows_view',
    'realty_type', 'floors_count', 'garbage_chute', 'passenger_lifts', 'cargo_lifts',
    'build_year', 'parking_type', 'lifts_count', 'ceiling_height',
    'is_emergency', 'gas_type', 'renovation_programm', 'heat_type', 'project_type',
    'entrances', 'material_type', 'is_mortgage_allowed', 'sale_type',
    'finish_date', 'is_premium', 'review_count', 'total_rate', 'name', 'buildings_count',
    'foundation_year', 'coordinates', 'metro', 'travel_type', 'travel_time',
    'address', 'county', 'district', 'street', 'house',
    'total_area', 'living_area', 'kitchen_area', 'agent_name', 'views_count'
]

print(f"Total fields parsed: {len(parsed_fields)}")

print("\nRENT-SPECIFIC FIELDS NOT IN PAGECHECK:")
missing_rent_fields = []
for key in rent_specific.keys():
    if key not in ['paymentPeriod', 'leaseTermType', 'deposit', 'prepayMonths', 
                   'utilitiesIncluded', 'clientFee', 'agentFee']:
        continue
    if rent_specific[key] is not None:
        missing_rent_fields.append(key)

if missing_rent_fields:
    for field in missing_rent_fields:
        print(f"  - {field}: {rent_specific[field]}")
else:
    print("  (all important rent fields are covered)")

