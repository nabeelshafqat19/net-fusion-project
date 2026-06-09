from starlette.middleware.sessions import SessionMiddleware
from typing import Optional
from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from passlib.context import CryptContext
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from urllib.parse import quote
import models
from database import engine, get_db
from fastapi.staticfiles import StaticFiles

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="NetFusion IT Store API")
app.add_middleware(SessionMiddleware, secret_key="super-secret-netfusion-key")
app.mount("/images", StaticFiles(directory="images"), name="images")
app.mount("/videos", StaticFiles(directory="videos"), name="videos")
# Sets up the Bcrypt password scrambler
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Tell FastAPI where your HTML files are located
templates = Jinja2Templates(directory="templates")

# Helper function to generate mailto link for quote requests
def generate_quote_mailto(vendor_email: str, product_name: str, product_brand: str = None, product_category: str = None, product_price: float = None):
    subject = f"Quote Request for {product_name}"
    
    if product_brand and product_category and product_price:
        body = f"""Hi,

I'm interested in getting a quote for the following product:

Product: {product_name}
Brand: {product_brand}
Category: {product_category}
Price: ${product_price:,.2f}

Please send me more details and a formal quote.

Thank you!"""
    else:
        body = f"""Hi,

I'm interested in getting a quote for {product_name}.

Please send me more details.

Thank you!"""
    
    mailto_link = f"mailto:{vendor_email}?subject={quote(subject)}&body={quote(body)}"
    return mailto_link

# Register the function as a Jinja2 filter
templates.env.filters['quote_mailto'] = generate_quote_mailto

# Also add it to globals so it can be called directly in templates
templates.env.globals['generate_quote_mailto'] = generate_quote_mailto

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to get vendor email
def get_vendor_email(db: Session):
    settings = db.query(models.Settings).first()
    if not settings:
        # Create default settings if not exists
        default_settings = models.Settings(vendor_email="vendor@netfusion.com")
        db.add(default_settings)
        db.commit()
        return "vendor@netfusion.com"
    return settings.vendor_email

# Helper function to check if user is admin
def check_admin_access(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    return user if user and user.is_admin else None

# UPDATED: The Homepage Route
@app.get("/")
def read_root(request: Request, db: Session = Depends(get_db)):
    # 1. Python grabs all the IT equipment from MySQL
    hardware_list = db.query(models.Product).all()
    vendor_email = get_vendor_email(db)
    
    # Add mailto links to each product
    for product in hardware_list:
        product.mailto_link = generate_quote_mailto(vendor_email, product.name)
    
    # 2. Python sends that data directly into your HTML file (Using Keyword Arguments!)
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"products": hardware_list, "vendor_email": vendor_email}
    )

# Keep your API route just in case you need it later
@app.get("/api/products")
def get_products(db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    return products
# The About Us Route
@app.get("/about")
def about_page(request: Request):
    # We don't need database products for this page, just the HTML template!
    return templates.TemplateResponse(
        request=request, 
        name="about.html", 
        context={}
    )

# --- SECURE ADMIN UPLOAD ROUTES ---
@app.get("/admin/add-product")
def get_add_product_page(request: Request):
    # SECURITY CHECK
    if not request.session.get("is_admin"):
        return RedirectResponse(url="/login", status_code=303)
        
    # NEW: Point Python to the 'admin' subfolder
    return templates.TemplateResponse(
        request=request, 
        name="admin/add_product.html", 
        context={}
    )

@app.post("/admin/add-product")
def process_add_product(
    request: Request,
    name: str = Form(...),
    brand: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    image_url: str = Form(...),
    new_category: str = Form(default=""),
    db: Session = Depends(get_db)
):
    # SECURITY CHECK
    if not request.session.get("is_admin"):
        return RedirectResponse(url="/login", status_code=303)
    
    # Use new category if provided, otherwise use selected category
    final_category = new_category if new_category else category
    
    new_product = models.Product(
        name=name, brand=brand, category=final_category, 
        description=description, price=price, image_url=image_url
    )
    db.add(new_product)
    db.commit()
    
    # Send the admin straight back to the catalog to see their new product
    return RedirectResponse(url="/products", status_code=303)

# Delete Product Route
@app.post("/admin/delete-product/{product_id}")
def delete_product(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db)
):
    # SECURITY CHECK
    if not request.session.get("is_admin"):
        return RedirectResponse(url="/login", status_code=303)
    
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    
    if not product:
        return RedirectResponse(url="/products", status_code=303)
    
    db.delete(product)
    db.commit()
    
    # Redirect back to products page
    return RedirectResponse(url="/products", status_code=303)
# The Products Catalog Route
# --- THE NEW FILTER & SEARCH ROUTE ---
@app.get("/products")
def products_page(
    request: Request, 
    search: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    sort: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # 1. Start with all products
    query = db.query(models.Product)

    # 2. Apply Filters if the user selected them
    if search:
        query = query.filter(models.Product.name.ilike(f"%{search}%"))
    if category:
        query = query.filter(models.Product.category == category)
    if brand:
        query = query.filter(models.Product.brand == brand)

    # 3. Apply Sorting (Price High/Low)
    if sort == "price_asc":
        query = query.order_by(models.Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(models.Product.price.desc())

    products = query.all()

    # 4. Get vendor email and organize products by category with mailto links
    vendor_email = get_vendor_email(db)
    products_by_category = {}
    for product in products:
        # Generate mailto link for each product
        product.mailto_link = generate_quote_mailto(vendor_email, product.name)
        
        if product.category not in products_by_category:
            products_by_category[product.category] = []
        products_by_category[product.category].append(product)

    # 5. Magically grab all unique Categories and Brands directly from MySQL for our dropdowns
    categories = [c[0] for c in db.query(models.Product.category).distinct().all() if c[0]]
    brands = [b[0] for b in db.query(models.Product.brand).distinct().all() if b[0]]

    return templates.TemplateResponse(
        request=request, 
        name="products.html", 
        context={
            "products_by_category": products_by_category,
            "categories": categories,
            "brands": brands,
            "vendor_email": vendor_email,
            "current_search": search,
            "current_category": category,
            "current_brand": brand,
            "current_sort": sort
        }
    )

# Product Detail Page
# Product Detail Page
@app.get("/product/{product_id}")
def product_detail(product_id: int, request: Request, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    vendor_email = get_vendor_email(db)
    
    if not product:
        return templates.TemplateResponse(
            request=request, name="404.html", context={"message": "Product not found"}, status_code=404
        )
    
    # NEW: Split the images for the JavaScript Slider
    image_list = [img.strip() for img in product.image_url.split(",")]
    
    # Generate mailto link with full product details
    product.mailto_link = generate_quote_mailto(vendor_email, product.name, product.brand, product.category, product.price)
    
    return templates.TemplateResponse(
        request=request,
        name="product_detail.html",
        # NEW: Pass 'images' to the template
        context={"product": product, "vendor_email": vendor_email, "images": image_list} 
    )

# --- ADMIN SETTINGS ROUTES ---
@app.get("/admin/settings")
def get_admin_settings(request: Request, db: Session = Depends(get_db)):
    admin_user = check_admin_access(request, db)
    
    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)
    
    settings = db.query(models.Settings).first()
    if not settings:
        settings = models.Settings(vendor_email="vendor@netfusion.com")
        db.add(settings)
        db.commit()
    
    return templates.TemplateResponse(
        request=request,
        name="admin_settings.html",
        context={"vendor_email": settings.vendor_email, "admin_user": admin_user}
    )

@app.post("/admin/settings/update-vendor-email")
def update_vendor_email(
    request: Request,
    vendor_email: str = Form(...),
    db: Session = Depends(get_db)
):
    admin_user = check_admin_access(request, db)
    
    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)
    
    settings = db.query(models.Settings).first()
    if not settings:
        settings = models.Settings(vendor_email=vendor_email)
        db.add(settings)
    else:
        settings.vendor_email = vendor_email
    
    db.commit()
    
    return templates.TemplateResponse(
        request=request,
        name="admin_settings.html",
        context={"vendor_email": vendor_email, "message": "Vendor email updated successfully!", "admin_user": admin_user}
    )

# --- AUTHENTICATION ROUTES ---

# 1. Show the Signup Page
@app.get("/signup")
def get_signup_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="signup.html", 
        context={}
    )

# 2. Process the Signup Form
@app.post("/signup")
def process_signup(
    request: Request, 
    full_name: str = Form(...), 
    email: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        return templates.TemplateResponse(
            request=request, 
            name="signup.html", 
            context={"error": "Email already registered."}
        )

    # Scramble the password and save the user
    hashed_pwd = pwd_context.hash(password)
    new_user = models.User(full_name=full_name, email=email, hashed_password=hashed_pwd)
    
    db.add(new_user)
    db.commit()
    
    # Redirect them to the login page after successful signup
    return RedirectResponse(url="/login", status_code=303)


# 3. Show the Login Page
@app.get("/login")
def get_login_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="login.html", 
        context={}
    )

# 4. Process the Login Form
@app.post("/login")
def process_login(
    request: Request, 
    email: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    # Find the user by email
    user = db.query(models.User).filter(models.User.email == email).first()
    
    # Check if user exists AND password matches the hash
    if not user or not pwd_context.verify(password, user.hashed_password):
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"error": "Invalid email or password."}
        )

    # --- THIS IS THE CRITICAL PART WE MIGHT HAVE MISSED ---
    # Give the browser the secure session cookies!
    request.session["user_id"] = user.id
    request.session["is_admin"] = user.is_admin
    request.session["user_name"] = user.full_name

    # If successful, redirect to homepage
    return RedirectResponse(url="/", status_code=303)

# Make a user admin (For initial setup - use with caution!)
@app.post("/make-admin/{email}")
def make_admin(email: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return {"error": "User not found"}
    
    user.is_admin = True
    db.commit()
    return {"message": f"User {email} is now an admin", "user": {"email": user.email, "is_admin": user.is_admin}}