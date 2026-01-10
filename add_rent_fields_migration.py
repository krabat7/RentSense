from app.parser.database import DB
from sqlalchemy import text

print("Adding rent-specific fields to offers_details table...")

alter_statements = [
    "ALTER TABLE offers_details ADD COLUMN payment_period VARCHAR(50) NULL",
    "ALTER TABLE offers_details ADD COLUMN lease_term_type VARCHAR(50) NULL",
    "ALTER TABLE offers_details ADD COLUMN deposit DECIMAL(11, 2) NULL",
    "ALTER TABLE offers_details ADD COLUMN prepay_months INT NULL",
    "ALTER TABLE offers_details ADD COLUMN utilities_included BOOLEAN NULL",
    "ALTER TABLE offers_details ADD COLUMN client_fee INT NULL",
    "ALTER TABLE offers_details ADD COLUMN agent_fee INT NULL",
]

with DB.engine.connect() as conn:
    for statement in alter_statements:
        try:
            conn.execute(text(statement))
            conn.commit()
            print(f"OK: {statement.split()[-1]}")
        except Exception as e:
            conn.rollback()
            if "Duplicate column name" in str(e) or "already exists" in str(e).lower() or "Duplicate" in str(e):
                print(f"SKIP (already exists): {statement.split()[-1]}")
            else:
                print(f"ERROR: {e}")

print("\nMigration completed!")

