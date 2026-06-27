from starlette.middleware.sessions import SessionMiddleware
from typing import Optional
from fastapi import FastAPI, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, Response
from werkzeug.security import generate_password_hash, check_password_hash
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from urllib.parse import quote
import models
from database import engine, get_db
from fastapi.staticfiles import StaticFiles
import io
import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation
import os # Make sure os is imported

# 1. INITIALIZE APP FIRST
models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="NetFusion IT Store API")

# 2. THEN CONFIGURE MIDDLEWARE AND MOUNTS
app.add_middleware(SessionMiddleware, secret_key="super-secret-netfusion-key")
app.mount("/images", StaticFiles(directory="images"), name="images")
app.mount("/videos", StaticFiles(directory="videos"), name="videos")
templates = Jinja2Templates(directory="templates")

# 3. THEN DEFINE THE MIDDLEWARE
@app.middleware("http")
async def add_logo_to_context(request: Request, call_next):
    # This now works because 'app' exists above
    db = next(get_db())
    settings = db.query(models.Settings).first()
    request.state.logo_url = settings.logo_url if settings and settings.logo_url else "/images/Logov1.png"
    response = await call_next(request)
    return response

# Ensure templates have access
templates.env.globals['logo_url'] = lambda: None # Placeholder
# Initialize database
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pure Comfort Store API")
app.add_middleware(SessionMiddleware, secret_key="super-secret-netfusion-key")
app.mount("/images", StaticFiles(directory="images"), name="images")
app.mount("/videos", StaticFiles(directory="videos"), name="videos")

# Tell FastAPI where your HTML files are located
templates = Jinja2Templates(directory="templates")

# Initialize passlib for legacy password verification
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Helper function to verify passwords
def verify_password(stored_hash: str, password: str) -> bool:
    if not stored_hash or not password:
        return False
    try:
        return check_password_hash(stored_hash, password)
    except (ValueError, Exception):
        try:
            return pwd_context.verify(password, stored_hash)
        except Exception:
            return False

# Helper function to generate mailto link for quote requests
def generate_quote_mailto(vendor_email: str, product_name: str, product_brand: str = None, product_category: str = None, product_price: float = None):
    subject = f"Inquiry for {product_name}"
    
    if product_brand and product_category and product_price:
        body = f"""Hi,

I'm interested in getting more information about the following product:

Product: {product_name}
Material: {product_brand}
Collection: {product_category}
Price: ${product_price:,.2f}

Please send me more details.

Thank you!"""
    else:
        body = f"""Hi,

I'm interested in getting more information about {product_name}.

Please send me more details.

Thank you!"""
    
    mailto_link = f"mailto:{vendor_email}?subject={quote(subject)}&body={quote(body)}"
    return mailto_link

templates.env.filters['quote_mailto'] = generate_quote_mailto
templates.env.globals['generate_quote_mailto'] = generate_quote_mailto

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_vendor_email(db: Session):
    settings = db.query(models.Settings).first()
    if not settings:
        default_settings = models.Settings(vendor_email="support@purecomfort.com")
        db.add(default_settings)
        db.commit()
        return "support@purecomfort.com"
    return settings.vendor_email

def check_admin_access(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.query(models.User).filter(models.User.id == user_id).first()
    return user if user and user.is_admin else None


# ==========================================
# PUBLIC STOREFRONT ROUTES
# ==========================================

@app.get("/")
def read_root(request: Request, db: Session = Depends(get_db)):
    hardware_list = db.query(models.Product).all()
    vendor_email = get_vendor_email(db)
    
    for product in hardware_list:
        product.mailto_link = generate_quote_mailto(vendor_email, product.name)
    
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"request": request, "products": hardware_list, "vendor_email": vendor_email}
    )

@app.get("/api/products")
def get_products(db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    return products

@app.get("/about")
def about_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="about.html", 
        context={"request": request}
    )

@app.get("/products")
def products_page(
    request: Request, 
    search: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    sort: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Product)

    if search:
        query = query.filter(models.Product.name.ilike(f"%{search}%"))
    if category:
        query = query.filter(models.Product.category == category)
    if brand:
        query = query.filter(models.Product.brand == brand)

    if sort == "price_asc":
        query = query.order_by(models.Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(models.Product.price.desc())

    products = query.all()

    vendor_email = get_vendor_email(db)
    products_by_category = {}
    for product in products:
        product.mailto_link = generate_quote_mailto(vendor_email, product.name)
        if product.category not in products_by_category:
            products_by_category[product.category] = []
        products_by_category[product.category].append(product)

    categories = [c[0] for c in db.query(models.Product.category).distinct().all() if c[0]]
    brands = [b[0] for b in db.query(models.Product.brand).distinct().all() if b[0]]

    return templates.TemplateResponse(
        request=request, 
        name="products.html", 
        context={
            "request": request,
            "products": products,
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

@app.get("/product/{product_id}")
def product_detail(product_id: int, request: Request, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    vendor_email = get_vendor_email(db)
    
    if not product:
        return templates.TemplateResponse(
            request=request, name="404.html", context={"request": request, "message": "Product not found"}, status_code=404
        )
    
    image_list = [img.strip() for img in product.image_url.split(",")]
    product.mailto_link = generate_quote_mailto(vendor_email, product.name, product.brand, product.category, product.price)
    
    return templates.TemplateResponse(
        request=request,
        name="product_detail.html",
        context={"request": request, "product": product, "vendor_email": vendor_email, "images": image_list} 
    )


# ==========================================
# SECURE ADMIN DASHBOARD ROUTES
# ==========================================

@app.get("/admin/dashboard")
async def admin_dashboard(request: Request, db: Session = Depends(get_db)): 
    if not request.session.get('is_admin'):
        return RedirectResponse(url="/login", status_code=303)

    product_count = db.query(models.Product).count()
    order_count = 0 

    return templates.TemplateResponse(
        request=request, 
        name="admin/dashboard.html", 
        context={
            "request": request, 
            "product_count": product_count,
            "order_count": order_count
        }
    )

@app.get("/admin/products")
async def admin_products_list(request: Request, db: Session = Depends(get_db)):
    if not request.session.get('is_admin'):
        return RedirectResponse(url="/login", status_code=303)

    db_products = db.query(models.Product).all() 

    return templates.TemplateResponse(
        request=request,
        name="admin/products.html", 
        context={
            "request": request, 
            "products": db_products
        }
    )

@app.get("/admin/add-product")
def get_add_product_page(request: Request):
    if not request.session.get("is_admin"):
        return RedirectResponse(url="/login", status_code=303)
        
    return templates.TemplateResponse(
        request=request, 
        name="admin/add_product.html", 
        context={"request": request}
    )

@app.post("/admin/add-product")
async def process_add_product(
    request: Request,
    name: str = Form(...),
    brand: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    image_url: str = Form(...),
    new_category: str = Form(default=""),
    in_stock: bool = Form(default=False),
    db: Session = Depends(get_db)
):
    if not request.session.get("is_admin"):
        return RedirectResponse(url="/login", status_code=303)
    
    final_category = new_category if new_category else category
    
    try:
        new_product = models.Product(
            name=name, 
            brand=brand, 
            category=final_category, 
            description=description, 
            price=price, 
            image_url=image_url,
            in_stock=in_stock
        )
        db.add(new_product)
        db.commit()
        
        return RedirectResponse(url="/admin/products", status_code=303)
        
    except Exception as e:
        print(f"DATABASE ERROR: {e}")
        db.rollback()
        return RedirectResponse(url="/admin/add-product", status_code=303)
        
@app.post("/admin/delete-product/{product_id}")
def delete_product(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db)
):
    if not request.session.get("is_admin"):
        return RedirectResponse(url="/login", status_code=303)
    
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        return RedirectResponse(url="/admin/products", status_code=303)
    
    db.delete(product)
    db.commit()
    return RedirectResponse(url="/admin/products", status_code=303)

@app.get("/admin/settings")
def get_admin_settings(request: Request, db: Session = Depends(get_db)):
    admin_user = check_admin_access(request, db)
    
    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)
    
    settings = db.query(models.Settings).first()
    if not settings:
        settings = models.Settings(vendor_email="support@purecomfort.com")
        db.add(settings)
        db.commit()
    
    return templates.TemplateResponse(
        request=request,
        name="admin_settings.html",
        context={"request": request, "vendor_email": settings.vendor_email, "admin_user": admin_user}
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
        context={"request": request, "vendor_email": vendor_email, "message": "Email updated successfully!", "admin_user": admin_user}
    )


# ==========================================
# EXCEL BULK UPLOAD & DOWNLOAD ROUTES
# ==========================================

@app.get("/admin/download-excel-template")
def download_excel_template(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("is_admin"):
        return RedirectResponse(url="/login", status_code=303)
    
    # 1. Create a real Excel Workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Products Template"
    
    # 2. Write Header Row
    headers = [
        'name', 'brand', 'category', 'price', 'description', 
        'image_url_1', 'image_url_2', 'image_url_3', 'image_url_4'
    ]
    ws.append(headers)
    
    # 3. Define the base categories that should ALWAYS be there
    base_categories = [
        "Servers & Data Center", 
        "Networking Equipment", 
        "Workstations & Laptops", 
        "Cybersecurity"
    ]
    
    # 4. Grab custom categories from the DB, filter out numbers and junk
    raw_db_categories = [c[0] for c in db.query(models.Product.category).distinct().all() if c[0]]
    db_categories = []
    
    for cat in raw_db_categories:
        cat_str = str(cat).strip()
        # Only keep if it's NOT just a number AND longer than 2 characters
        if not cat_str.isnumeric() and len(cat_str) > 2:
            db_categories.append(cat_str)
            
    # 5. MERGE lists, remove duplicates, and sort alphabetically
    all_categories = list(set(base_categories + db_categories))
    all_categories.sort()
    
    # 6. Create the Dropdown Data Validation
    dropdown_formula = f'"{",".join(all_categories)}"'
    dv = DataValidation(type="list", formula1=dropdown_formula, allow_blank=False)
    
    dv.error = 'Your entry is not in the list. Please select a category from the dropdown.'
    dv.errorTitle = 'Invalid Category'
    
    ws.add_data_validation(dv)
    dv.add('C2:C1000') # Applies the dropdown to the first 1000 rows
    
    # 7. Write an example row
    ws.append([
        'Dell PowerEdge R750',
        'Dell',
        "Servers & Data Center", 
        2499.99,
        'High-performance enterprise server.',
        'https://example.com/img1.jpg',
        '', '', ''
    ])
    
    # 8. Save to memory and return safely to prevent 500 errors
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=netfusion_template.xlsx"}
    )


@app.post("/admin/bulk-upload-products")
async def bulk_upload_products(
    request: Request,
    excel_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not request.session.get("is_admin"):
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        # Read the actual Excel file using openpyxl
        contents = await excel_file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True)
        ws = wb.active
        
        # Get all rows
        rows = list(ws.values)
        if len(rows) < 2:
            return RedirectResponse(url="/admin/products", status_code=303)
            
        headers = rows[0]
        
        # Loop through data starting at row 2
        for row in rows[1:]:
            row_dict = dict(zip(headers, row))
            
            # Skip empty rows
            if not row_dict.get('name'):
                continue
                
            # Combine the 4 Image URLs
            urls = [
                str(row_dict.get('image_url_1') or '').strip(),
                str(row_dict.get('image_url_2') or '').strip(),
                str(row_dict.get('image_url_3') or '').strip(),
                str(row_dict.get('image_url_4') or '').strip()
            ]
            valid_urls = [u for u in urls if u and u != 'None']
            combined_images = ",".join(valid_urls)
            
            # Clean the price
            try:
                price_str = str(row_dict.get('price', '0')).replace(',', '').replace('$', '')
                price = float(price_str)
            except ValueError:
                price = 0.0
            
            new_product = models.Product(
                name=str(row_dict.get('name', '')).strip(),
                brand=str(row_dict.get('brand', '')).strip(),
                category=str(row_dict.get('category', '')).strip(),
                price=price,
                description=str(row_dict.get('description', '')).strip(),
                image_url=combined_images,
                in_stock=True
            )
            db.add(new_product)
            
        db.commit()
        return RedirectResponse(url="/admin/products", status_code=303)
        
    except Exception as e:
        print(f"EXCEL UPLOAD ERROR: {e}")
        db.rollback()
        return RedirectResponse(url="/admin/products", status_code=303)


# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.get("/signup")
def get_signup_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="signup.html", 
        context={"request": request}
    )

@app.post("/signup")
def process_signup(
    request: Request, 
    full_name: str = Form(...), 
    email: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        return templates.TemplateResponse(
            request=request, 
            name="signup.html", 
            context={"request": request, "error": "Email already registered."}
        )

    hashed_pwd = generate_password_hash(password)
    new_user = models.User(full_name=full_name, email=email, hashed_password=hashed_pwd)
    
    db.add(new_user)
    db.commit()
    
    return RedirectResponse(url="/login", status_code=303)

@app.get("/login")
def get_login_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="login.html", 
        context={"request": request}
    )

@app.post("/login")
def process_login(
    request: Request, 
    email: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()
    
    if not user:
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"request": request, "error": "Invalid email or password."}
        )
    
    if not verify_password(user.hashed_password, password):
        return templates.TemplateResponse(
            request=request, 
            name="login.html", 
            context={"request": request, "error": "Invalid email or password."}
        )

    request.session["user_id"] = user.id
    request.session["is_admin"] = user.is_admin
    request.session["user_name"] = user.full_name

    return RedirectResponse(url="/", status_code=303)

@app.post("/make-admin/{email}")
def make_admin(email: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return {"error": "User not found"}
    
    user.is_admin = True
    db.commit()
    return {"message": f"User {email} is now an admin", "user": {"email": user.email, "is_admin": user.is_admin}}

@app.post("/admin/settings/update-logo")
async def update_logo(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not request.session.get("is_admin"):
        return RedirectResponse(url="/login", status_code=303)
    
    # Save the file to the images folder
    os.makedirs("images", exist_ok=True)
    file_path = os.path.join("images", "logo.png") 
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    # Update DB
    settings = db.query(models.Settings).first()
    if not settings:
        settings = models.Settings(logo_url="/images/logo.png")
        db.add(settings)
    else:
        settings.logo_url = "/images/logo.png"
    db.commit()
    
    return RedirectResponse(url="/admin/dashboard", status_code=303)