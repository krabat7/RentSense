import logging
from dotenv import dotenv_values
from sqlalchemy import DECIMAL, Column, ForeignKey, create_engine, text, JSON, Boolean, Integer, BigInteger, String, DateTime
from sqlalchemy.dialects.mysql import TEXT, TIMESTAMP
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import declarative_base, relationship, scoped_session, sessionmaker

Base = declarative_base()
from pathlib import Path
env_path = Path(__file__).parent.parent.parent / '.env'
env = dotenv_values(env_path)
DBTYPE = env.get('DB_TYPE') or 'mysql+pymysql'
LOGIN = env.get('DB_LOGIN') or 'root'
PASS = env.get('DB_PASS') or 'rootpassword'
IP = env.get('DB_IP') or 'localhost'
PORT = env.get('DB_PORT') or '3307'
DBNAME = env.get('DB_NAME') or 'rentsense'
DATABASE_URL = f'{DBTYPE}://{LOGIN}:{PASS}@{IP}:{PORT}/{DBNAME}?charset=utf8mb4'


class Offers(Base):
    __tablename__ = 'offers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    cian_id = Column(BigInteger, nullable=False, unique=True, index=True)
    price = Column(DECIMAL(15, 2), nullable=False)
    category = Column(String(255), nullable=True)
    views_count = Column(Integer, nullable=True)
    photos_count = Column(Integer, nullable=True)
    floor_number = Column(Integer, nullable=True)
    floors_count = Column(Integer, nullable=True)
    publication_at = Column(Integer, nullable=True)
    price_changes = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    address = relationship("Addresses", back_populates="offer", uselist=False)
    realty_inside = relationship("Realty_inside", back_populates="offer", uselist=False, cascade="all, delete-orphan")
    realty_outside = relationship("Realty_outside", back_populates="offer", uselist=False, cascade="all, delete-orphan")
    realty_details = relationship("Realty_details", back_populates="offer", uselist=False, cascade="all, delete-orphan")
    offers_details = relationship("Offers_details", back_populates="offer", uselist=False, cascade="all, delete-orphan")
    developer = relationship("Developers", back_populates="offer", uselist=False, cascade="all, delete-orphan")
    photos = relationship("Photos", back_populates="offer", cascade="all, delete-orphan", order_by="Photos.order_index")


class Addresses(Base):
    __tablename__ = 'addresses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    cian_id = Column(BigInteger, ForeignKey('offers.cian_id'), index=True)
    county = Column(String(255), nullable=True, index=True)
    district = Column(String(255), nullable=True, index=True)
    street = Column(String(255), nullable=True, index=True)
    house = Column(String(255), nullable=True)
    metro = Column(String(255), nullable=True)
    travel_type = Column(String(255), nullable=True)
    travel_time = Column(Integer, nullable=True)
    address = Column(JSON, nullable=True)
    coordinates = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    offer = relationship("Offers", back_populates="address", uselist=False)


class Realty_inside(Base):
    __tablename__ = 'realty_inside'

    id = Column(Integer, primary_key=True, autoincrement=True)
    cian_id = Column(BigInteger, ForeignKey('offers.cian_id'), index=True)
    repair_type = Column(String(255), nullable=True, index=True)
    total_area = Column(DECIMAL(11, 2), nullable=True, index=True)
    living_area = Column(DECIMAL(11, 2), nullable=True)
    kitchen_area = Column(DECIMAL(11, 2), nullable=True)
    ceiling_height = Column(DECIMAL(11, 2), nullable=True)
    balconies = Column(Integer, nullable=True)
    loggias = Column(Integer, nullable=True)
    rooms_count = Column(Integer, nullable=True)
    separated_wc = Column(Integer, nullable=True)
    combined_wc = Column(Integer, nullable=True)
    windows_view = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    offer = relationship("Offers", back_populates="realty_inside", uselist=False)


class Realty_outside(Base):
    __tablename__ = 'realty_outside'

    id = Column(Integer, primary_key=True, autoincrement=True)
    cian_id = Column(BigInteger, ForeignKey('offers.cian_id'), index=True)
    build_year = Column(Integer, nullable=True, index=True)
    entrances = Column(Integer, nullable=True)
    material_type = Column(String(255), nullable=True)
    parking_type = Column(String(255), nullable=True)
    garbage_chute = Column(Boolean, nullable=True)
    lifts_count = Column(Integer, nullable=True)
    passenger_lifts = Column(Integer, nullable=True)
    cargo_lifts = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    offer = relationship("Offers", back_populates="realty_outside", uselist=False)


class Realty_details(Base):
    __tablename__ = 'realty_details'

    id = Column(Integer, primary_key=True, autoincrement=True)
    cian_id = Column(BigInteger, ForeignKey('offers.cian_id'), index=True)
    realty_type = Column(String(255), nullable=True, index=True)
    project_type = Column(String(255), nullable=True)
    heat_type = Column(String(255), nullable=True)
    gas_type = Column(String(255), nullable=True)
    is_apartment = Column(Boolean, nullable=True)
    is_penthouse = Column(Boolean, nullable=True)
    is_mortgage_allowed = Column(Boolean, nullable=True)
    is_premium = Column(Boolean, nullable=True)
    is_emergency = Column(Boolean, nullable=True)
    renovation_programm = Column(Boolean, nullable=True)
    finish_date = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    offer = relationship("Offers", back_populates="realty_details", uselist=False)


class Offers_details(Base):
    __tablename__ = 'offers_details'

    id = Column(Integer, primary_key=True, autoincrement=True)
    cian_id = Column(BigInteger, ForeignKey('offers.cian_id'), index=True)
    agent_name = Column(String(255), nullable=True)
    deal_type = Column(String(255), nullable=True)
    flat_type = Column(String(255), nullable=True)
    sale_type = Column(String(255), nullable=True)
    is_duplicate = Column(Boolean, nullable=True)
    description = Column(TEXT, nullable=True)
    payment_period = Column(String(50), nullable=True)
    lease_term_type = Column(String(50), nullable=True)
    deposit = Column(DECIMAL(11, 2), nullable=True)
    prepay_months = Column(Integer, nullable=True)
    utilities_included = Column(Boolean, nullable=True)
    client_fee = Column(Integer, nullable=True)
    agent_fee = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    offer = relationship("Offers", back_populates="offers_details", uselist=False)


class Developers(Base):
    __tablename__ = 'developers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    cian_id = Column(BigInteger, ForeignKey('offers.cian_id'), index=True)
    name = Column(String(255), nullable=True)
    review_count = Column(Integer, nullable=True)
    total_rate = Column(DECIMAL(2, 1), nullable=True)
    buildings_count = Column(Integer, nullable=True)
    foundation_year = Column(Integer, nullable=True)
    is_reliable = Column(Boolean, nullable=True)
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    offer = relationship("Offers", back_populates="developer", uselist=False)


class Photos(Base):
    __tablename__ = 'photos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    cian_id = Column(BigInteger, ForeignKey('offers.cian_id'), index=True)
    url = Column(String(1000), nullable=False)  # URL оригинального фото
    local_path = Column(String(500), nullable=True)  # Путь к скачанному файлу (если скачано)
    order_index = Column(Integer, nullable=True)  # Порядковый номер фото (0, 1, 2...)
    is_downloaded = Column(Boolean, default=False)  # Скачано ли фото локально
    downloaded_at = Column(DateTime, nullable=True)  # Когда было скачано
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    
    offer = relationship("Offers", back_populates="photos")


class DatabaseManager:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, pool_pre_ping=True, future=True, connect_args={"connect_timeout": 10})
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        try:
            self.create_tables()
        except Exception as e:
            logging.warning(f"Could not create tables on init: {e}. Will retry later.")

    def create_tables(self):
        existing_tables = self.get_existing_tables()
        Base.metadata.create_all(self.engine)

    def get_existing_tables(self):
        session = self.Session()
        try:
            connection = session.connection()
            existing_tables = connection.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()")).fetchall()
            return {table_name for (table_name,) in existing_tables}
        finally:
            session.close()

    def insert(self, *instances):
        session = self.Session()
        try:
            session.add_all(instances)
            session.commit()
            logging.info("Insert successful")
        except (IntegrityError, SQLAlchemyError) as e:
            session.rollback()
            if isinstance(e, IntegrityError) and 'Duplicate entry' in str(e.orig):
                logging.error(f"Integrity error during insertion: Duplicate entry")
            else:
                logging.error(f"Error during insertion: {e}", exc_info=True)
        finally:
            session.close()

    def update(self, model_class, filter_conditions, update_values):
        session = self.Session()
        try:
            updated_rows = session.query(model_class).filter_by(**filter_conditions).update(update_values)
            if updated_rows == 0:
                logging.error("No records found to update with conditions: %s", filter_conditions)
                return
            session.commit()
            logging.info("Update successful")
        except SQLAlchemyError as e:
            session.rollback()
            logging.error(f"Error during update: {e}", exc_info=True)
        finally:
            session.close()

    def select(self, model_class, filter=None, filter_by=None, limit=None, order_by=None, distinct=False):
        session = self.Session()
        try:
            query = session.query(model_class)
            if distinct:
                query = query.distinct()
            if filter_by:
                query = query.filter_by(**filter_by)
            elif filter:
                query = query.filter(*filter)
            if order_by:
                query = query.order_by(order_by)
            if limit:
                query = query.limit(limit)
            return query.all()
        finally:
            session.close()

    def close(self):
        self.Session.remove()


model_classes = {
    "offers": Offers,
    "addresses": Addresses,
    "realty_inside": Realty_inside,
    "realty_outside": Realty_outside,
    "realty_details": Realty_details,
    "offers_details": Offers_details,
    "developers": Developers,
    "photos": Photos,
}

DB = DatabaseManager(DATABASE_URL)
