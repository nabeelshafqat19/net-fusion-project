import io
import os
from urllib.parse import quote

import openpyxl
from flask import (
    Flask,
    abort,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from openpyxl.worksheet.datavalidation import DataValidation
from passlib.context import CryptContext
from werkzeug.security import check_password_hash, generate_password_hash

import models
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-netfusion-key")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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


def generate_quote_mailto(
    vendor_email: str,
    product_name: str,
    product_brand: str = None,
    product_category: str = None,
    product_price: float = None,
):
    subject = f"Inquiry for {product_name}"

    if product_brand and product_category and product_price is not None:
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

    return f"mailto:{vendor_email}?subject={quote(subject)}&body={quote(body)}"


app.jinja_env.filters["quote_mailto"] = generate_quote_mailto
app.jinja_env.globals["generate_quote_mailto"] = generate_quote_mailto


@app.before_request
def open_db():
    g.db = SessionLocal()


@app.teardown_request
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def get_vendor_email(db):
    settings = db.query(models.Settings).first()
    if not settings:
        default_settings = models.Settings(vendor_email="support@purecomfort.com")
        db.add(default_settings)
        db.commit()
        return "support@purecomfort.com"
    return settings.vendor_email


def check_admin_access(db):
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = db.query(models.User).filter(models.User.id == user_id).first()
    return user if user and user.is_admin else None


def product_to_dict(product):
    return {
        "id": product.id,
        "name": product.name,
        "brand": product.brand,
        "category": product.category,
        "description": product.description,
        "price": product.price,
        "in_stock": product.in_stock,
        "image_url": product.image_url,
    }


@app.context_processor
def inject_template_globals():
    logo_url = "/images/Logov1.png"
    vendor_email = "support@purecomfort.com"

    db = g.get("db")
    if db is not None:
        settings = db.query(models.Settings).first()
        if settings:
            if settings.logo_url:
                logo_url = settings.logo_url
            if settings.vendor_email:
                vendor_email = settings.vendor_email

    return {
        "logo_url": logo_url,
        "vendor_email": vendor_email,
    }


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


@app.route("/images/<path:filename>")
def serve_images(filename):
    return send_from_directory(os.path.join(app.root_path, "images"), filename)


@app.route("/videos/<path:filename>")
def serve_videos(filename):
    return send_from_directory(os.path.join(app.root_path, "videos"), filename)


# ==========================================
# PUBLIC STOREFRONT ROUTES
# ==========================================


@app.route("/", methods=["GET"])
def read_root():
    db = g.db
    hardware_list = db.query(models.Product).all()
    vendor_email = get_vendor_email(db)

    for product in hardware_list:
        product.mailto_link = generate_quote_mailto(vendor_email, product.name)

    return render_template(
        "index.html",
        products=hardware_list,
        vendor_email=vendor_email,
    )


@app.route("/api/products", methods=["GET"])
def get_products():
    products = g.db.query(models.Product).all()
    return jsonify([product_to_dict(p) for p in products])


@app.route("/about", methods=["GET"])
def about_page():
    return render_template("About.html")


@app.route("/products", methods=["GET"])
def products_page():
    db = g.db
    search = request.args.get("search")
    category = request.args.get("category")
    brand = request.args.get("brand")
    sort = request.args.get("sort")

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

    return render_template(
        "products.html",
        products=products,
        products_by_category=products_by_category,
        categories=categories,
        brands=brands,
        vendor_email=vendor_email,
        current_search=search,
        current_category=category,
        current_brand=brand,
        current_sort=sort,
    )


@app.route("/product/<int:product_id>", methods=["GET"])
def product_detail(product_id):
    db = g.db
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    vendor_email = get_vendor_email(db)

    if not product:
        abort(404)

    image_list = [img.strip() for img in (product.image_url or "").split(",") if img.strip()]
    product.mailto_link = generate_quote_mailto(
        vendor_email, product.name, product.brand, product.category, product.price
    )

    return render_template(
        "product_detail.html",
        product=product,
        vendor_email=vendor_email,
        images=image_list,
    )


# ==========================================
# SECURE ADMIN DASHBOARD ROUTES
# ==========================================


@app.route("/admin/dashboard", methods=["GET"])
def admin_dashboard():
    if not session.get("is_admin"):
        return redirect(url_for("get_login_page"))

    product_count = g.db.query(models.Product).count()
    order_count = 0

    return render_template(
        "admin/dashboard.html",
        product_count=product_count,
        order_count=order_count,
    )


@app.route("/admin/products", methods=["GET"])
def admin_products_list():
    if not session.get("is_admin"):
        return redirect(url_for("get_login_page"))

    db_products = g.db.query(models.Product).all()

    return render_template("admin/products.html", products=db_products)


@app.route("/admin/add-product", methods=["GET"])
def get_add_product_page():
    if not session.get("is_admin"):
        return redirect(url_for("get_login_page"))

    return render_template("admin/add_product.html")


@app.route("/admin/add-product", methods=["POST"])
def process_add_product():
    if not session.get("is_admin"):
        return redirect(url_for("get_login_page"))

    db = g.db
    name = request.form.get("name", "").strip()
    brand = request.form.get("brand", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    image_url = request.form.get("image_url", "").strip()
    new_category = request.form.get("new_category", "").strip()
    in_stock = request.form.get("in_stock") in ("on", "true", "1", "yes")

    try:
        price = float(request.form.get("price", "0"))
    except ValueError:
        price = 0.0

    final_category = new_category if new_category else category

    try:
        new_product = models.Product(
            name=name,
            brand=brand,
            category=final_category,
            description=description,
            price=price,
            image_url=image_url,
            in_stock=in_stock,
        )
        db.add(new_product)
        db.commit()
        return redirect(url_for("admin_products_list"))
    except Exception as e:
        print(f"DATABASE ERROR: {e}")
        db.rollback()
        return redirect(url_for("get_add_product_page"))


@app.route("/admin/delete-product/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    if not session.get("is_admin"):
        return redirect(url_for("get_login_page"))

    db = g.db
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        return redirect(url_for("admin_products_list"))

    db.delete(product)
    db.commit()
    return redirect(url_for("admin_products_list"))


@app.route("/admin/settings", methods=["GET"])
def get_admin_settings():
    db = g.db
    admin_user = check_admin_access(db)

    if not admin_user:
        return redirect(url_for("get_login_page"))

    settings = db.query(models.Settings).first()
    if not settings:
        settings = models.Settings(vendor_email="support@purecomfort.com")
        db.add(settings)
        db.commit()

    return render_template(
        "admin_settings.html",
        vendor_email=settings.vendor_email,
        admin_user=admin_user,
    )


@app.route("/admin/settings/update-vendor-email", methods=["POST"])
def update_vendor_email():
    db = g.db
    admin_user = check_admin_access(db)

    if not admin_user:
        return redirect(url_for("get_login_page"))

    vendor_email = request.form.get("vendor_email", "").strip()
    settings = db.query(models.Settings).first()
    if not settings:
        settings = models.Settings(vendor_email=vendor_email)
        db.add(settings)
    else:
        settings.vendor_email = vendor_email

    db.commit()

    return render_template(
        "admin_settings.html",
        vendor_email=vendor_email,
        message="Email updated successfully!",
        admin_user=admin_user,
    )


# ==========================================
# EXCEL BULK UPLOAD & DOWNLOAD ROUTES
# ==========================================


@app.route("/admin/download-excel-template", methods=["GET"])
def download_excel_template():
    if not session.get("is_admin"):
        return redirect(url_for("get_login_page"))

    db = g.db
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Products Template"

    headers = [
        "name",
        "brand",
        "category",
        "price",
        "description",
        "image_url_1",
        "image_url_2",
        "image_url_3",
        "image_url_4",
    ]
    ws.append(headers)

    base_categories = [
        "Servers & Data Center",
        "Networking Equipment",
        "Workstations & Laptops",
        "Cybersecurity",
    ]

    raw_db_categories = [c[0] for c in db.query(models.Product.category).distinct().all() if c[0]]
    db_categories = []

    for cat in raw_db_categories:
        cat_str = str(cat).strip()
        if not cat_str.isnumeric() and len(cat_str) > 2:
            db_categories.append(cat_str)

    all_categories = list(set(base_categories + db_categories))
    all_categories.sort()

    dropdown_formula = f'"{",".join(all_categories)}"'
    dv = DataValidation(type="list", formula1=dropdown_formula, allow_blank=False)
    dv.error = "Your entry is not in the list. Please select a category from the dropdown."
    dv.errorTitle = "Invalid Category"

    ws.add_data_validation(dv)
    dv.add("C2:C1000")

    ws.append([
        "Dell PowerEdge R750",
        "Dell",
        "Servers & Data Center",
        2499.99,
        "High-performance enterprise server.",
        "https://example.com/img1.jpg",
        "",
        "",
        "",
    ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="netfusion_template.xlsx",
    )


@app.route("/admin/bulk-upload-products", methods=["POST"])
def bulk_upload_products():
    if not session.get("is_admin"):
        return redirect(url_for("get_login_page"))

    db = g.db
    excel_file = request.files.get("excel_file")

    if not excel_file or not excel_file.filename:
        return redirect(url_for("admin_products_list"))

    try:
        contents = excel_file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True)
        ws = wb.active

        rows = list(ws.values)
        if len(rows) < 2:
            return redirect(url_for("admin_products_list"))

        headers = rows[0]

        for row in rows[1:]:
            row_dict = dict(zip(headers, row))

            if not row_dict.get("name"):
                continue

            urls = [
                str(row_dict.get("image_url_1") or "").strip(),
                str(row_dict.get("image_url_2") or "").strip(),
                str(row_dict.get("image_url_3") or "").strip(),
                str(row_dict.get("image_url_4") or "").strip(),
            ]
            valid_urls = [u for u in urls if u and u != "None"]
            combined_images = ",".join(valid_urls)

            try:
                price_str = str(row_dict.get("price", "0")).replace(",", "").replace("$", "")
                price = float(price_str)
            except ValueError:
                price = 0.0

            new_product = models.Product(
                name=str(row_dict.get("name", "")).strip(),
                brand=str(row_dict.get("brand", "")).strip(),
                category=str(row_dict.get("category", "")).strip(),
                price=price,
                description=str(row_dict.get("description", "")).strip(),
                image_url=combined_images,
                in_stock=True,
            )
            db.add(new_product)

        db.commit()
        return redirect(url_for("admin_products_list"))

    except Exception as e:
        print(f"EXCEL UPLOAD ERROR: {e}")
        db.rollback()
        return redirect(url_for("admin_products_list"))


# ==========================================
# AUTHENTICATION ROUTES
# ==========================================


@app.route("/signup", methods=["GET"])
def get_signup_page():
    return render_template("signup.html")


@app.route("/signup", methods=["POST"])
def process_signup():
    db = g.db
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        return render_template("signup.html", error="Email already registered.")

    hashed_pwd = generate_password_hash(password)
    new_user = models.User(full_name=full_name, email=email, hashed_password=hashed_pwd)

    db.add(new_user)
    db.commit()

    return redirect(url_for("get_login_page"))


@app.route("/login", methods=["GET"])
def get_login_page():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def process_login():
    db = g.db
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        return render_template("login.html", error="Invalid email or password.")

    if not verify_password(user.hashed_password, password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = user.id
    session["is_admin"] = user.is_admin
    session["user_name"] = user.full_name

    return redirect(url_for("read_root"))


@app.route("/make-admin/<email>", methods=["POST"])
def make_admin(email):
    db = g.db
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.is_admin = True
    db.commit()
    return jsonify({
        "message": f"User {email} is now an admin",
        "user": {"email": user.email, "is_admin": user.is_admin},
    })


@app.route("/admin/settings/update-logo", methods=["POST"])
def update_logo():
    if not session.get("is_admin"):
        return redirect(url_for("get_login_page"))

    db = g.db
    file = request.files.get("file")

    if not file or not file.filename:
        return redirect(url_for("admin_dashboard"))

    os.makedirs(os.path.join(app.root_path, "images"), exist_ok=True)
    file_path = os.path.join(app.root_path, "images", "logo.png")

    file.save(file_path)

    settings = db.query(models.Settings).first()
    if not settings:
        settings = models.Settings(logo_url="/images/logo.png")
        db.add(settings)
    else:
        settings.logo_url = "/images/logo.png"
    db.commit()

    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
