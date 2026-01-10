from app.parser.database import DB, Offers
from sqlalchemy import text

with DB.engine.connect() as conn:
    conn.execute(text("DELETE FROM offers WHERE cian_id = 311739319"))
    conn.commit()
    print("Deleted offer 311739319")

import sys
sys.path.insert(0, '.')
from app.parser.main import apartPage

result = apartPage(['311739319'], dbinsert=True)
print(f"Reparsed, result: {result}")

from app.parser.database import Offers_details
details = DB.select(Offers_details, filter_by={'cian_id': 311739319})
if details:
    d = details[0]
    print("\nRent-specific fields:")
    print(f"  payment_period: {d.payment_period}")
    print(f"  lease_term_type: {d.lease_term_type}")
    print(f"  deposit: {d.deposit}")
    print(f"  prepay_months: {d.prepay_months}")
    print(f"  utilities_included: {d.utilities_included}")
    print(f"  client_fee: {d.client_fee}")
    print(f"  agent_fee: {d.agent_fee}")

