from sqlalchemy import Column, Integer, String, Float, Text, Boolean
from database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True)
    brand = Column(String(100), index=True)
    category = Column(String(100), index=True) 
    description = Column(Text)
    price = Column(Float)
    in_stock = Column(Boolean, default=True)
    image_url = Column(String(255))

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    
    is_admin = Column(Boolean, default=False)

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    vendor_email = Column(String(255), default="vendor@netfusion.com")