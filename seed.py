from database import SessionLocal
from models import Product

def seed_database():
    # Open a connection to the database
    db = SessionLocal()

    # Check if we already have products so we don't accidentally double-add them
    if db.query(Product).count() == 0:
        print("Adding IT Equipment to the database...")

        # Create our sample NetFusion products
        products = [
            Product(
                name="Dell PowerEdge R750 Rack Server",
                category="Servers & Data Center",
                description="Enterprise-grade 2U rack server optimized for application acceleration and high-performance computing.",
                price=4500.00,
                in_stock=True,
                image_url="https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=800&q=80"
            ),
            Product(
                name="Cisco Catalyst 9300 Series Switch",
                category="Networking Equipment",
                description="Industry-leading enterprise switching platform built for security, IoT, mobility, and cloud.",
                price=2800.00,
                in_stock=True,
                image_url="https://images.unsplash.com/photo-1544197150-b99a580bb7a8?auto=format&fit=crop&w=800&q=80"
            ),
            Product(
                name="Lenovo ThinkStation P620",
                category="Workstations & Laptops",
                description="Powerhouse workstation featuring AMD Threadripper PRO, designed for heavy 3D rendering and AI development.",
                price=3200.00,
                in_stock=True,
                image_url="https://images.unsplash.com/photo-1593640408182-31c70c8268f5?auto=format&fit=crop&w=800&q=80"
            )
        ]

        # Add them to the database and save (commit)
        db.add_all(products)
        db.commit()
        print("Successfully added products!")
    else:
        print("Database already has products in it. Skipping.")

    # Close the connection
    db.close()

if __name__ == "__main__":
    seed_database()