from app.parser.database import DB, Offers

offers = DB.select(Offers, filter_by={'cian_id': 311739319})
print(f'Found in DB: {len(offers) > 0}')
if offers:
    o = offers[0]
    print(f'Price: {o.price}')
    print(f'Floor: {o.floor_number}')
    print(f'Category: {o.category}')

