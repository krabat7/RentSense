import sys
sys.path.insert(0, '.')

from app.parser.main import getResponse, prePage

test_id = "311739319"

for attempt in range(3):
    print(f"\nAttempt {attempt + 1}...")
    response = getResponse(test_id, type=1, dbinsert=False)
    if response and '"offerData":' in response:
        print(f"SUCCESS: Got response with offerData, length: {len(response)}")
        pageJS = prePage(response, type=1)
        if pageJS and 'offer' in pageJS:
            offer = pageJS['offer']
            print(f"Offer ID: {offer.get('cianId')}")
            print(f"Price: {offer.get('priceTotalRur')}")
            print(f"Deal Type: {offer.get('dealType')}")
            print(f"oblId: {offer.get('trackingData', {}).get('oblId')}")
            
            if offer.get('cianId') and offer.get('priceTotalRur'):
                if offer.get('trackingData', {}).get('oblId') == 1:
                    print("All checks passed!")
                    break
                else:
                    print(f"oblId check failed: {offer.get('trackingData', {}).get('oblId')} != 1")
            else:
                print("Missing cianId or priceTotalRur")
        break
    else:
        print(f"Failed to get response or offerData")

