import sys
sys.path.insert(0, '.')

from app.parser.main import getResponse, prePage
from app.parser.pagecheck import pagecheck
from app.parser.database import DB, model_classes

test_id = "311739319"

print("Getting fresh data...")
response = getResponse(test_id, type=1, dbinsert=False)
if not response:
    print("No response")
    sys.exit(1)

pageJS = prePage(response, type=1)
if not pageJS:
    print("No pageJS")
    sys.exit(1)

data = pagecheck(pageJS)
if not data:
    print("Failed to parse data")
    sys.exit(1)

print("Updating existing offer...")
instances = [(model, data[key])
             for key, model in model_classes.items() if key in data]

for model, update_values in instances:
    print(f"Updating {model.__tablename__}...")
    DB.update(model, {'cian_id': test_id}, update_values)

print("\nChecking updated fields...")
from app.parser.database import Offers_details
details = DB.select(Offers_details, filter_by={'cian_id': int(test_id)})
if details:
    d = details[0]
    print("Rent-specific fields:")
    print(f"  payment_period: {d.payment_period}")
    print(f"  lease_term_type: {d.lease_term_type}")
    print(f"  deposit: {d.deposit}")
    print(f"  prepay_months: {d.prepay_months}")
    print(f"  utilities_included: {d.utilities_included}")
    print(f"  client_fee: {d.client_fee}")
    print(f"  agent_fee: {d.agent_fee}")

