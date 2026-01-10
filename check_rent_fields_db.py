from app.parser.database import DB, Offers_details

details = DB.select(Offers_details, filter_by={'cian_id': 311739319})
if details:
    d = details[0]
    print("Rent-specific fields in DB:")
    print(f"  payment_period: {d.payment_period}")
    print(f"  lease_term_type: {d.lease_term_type}")
    print(f"  deposit: {d.deposit}")
    print(f"  prepay_months: {d.prepay_months}")
    print(f"  utilities_included: {d.utilities_included}")
    print(f"  client_fee: {d.client_fee}")
    print(f"  agent_fee: {d.agent_fee}")
else:
    print("No data found")

