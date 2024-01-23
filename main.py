from flask import Flask, render_template, request, redirect, url_for, abort, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from flask_ckeditor import CKEditor
from forms import inputProduct, inputCategory, editProduct, deleteCategoryForm
from flask_bootstrap import Bootstrap5
from base64 import b64encode
from functools import wraps
import stripe
import os

stripe.api_key = os.environ.get("STRIPE_API_KEY")
endpoint_secret = os.environ.get("ENDPOINT_SECRET")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DATABASE_URI")


db = SQLAlchemy()
db.init_app(app)
login_manager = LoginManager(app)
login_manager.init_app(app)
CKEditor(app)
Bootstrap5(app)


###########################  DATABASE ########################
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    permission = db.Column(db.Integer, nullable=False)
    products = db.relationship("Product", back_populates="owner")
    basketProducts = db.relationship("BasketProduct", back_populates="user")

class Cookie(db.Model):
    __tablename__ = "cookies"
    id = db.Column(db.Integer, primary_key=True)
    basket_products = db.relationship("BasketProduct", back_populates="cookie")


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    location = db.Column(db.String, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    image = db.Column(db.LargeBinary, nullable=False)
    image_mimetype = db.Column(db.String, nullable=False)
    owner = db.relationship("User", back_populates="products")
    basketProducts = db.relationship("BasketProduct", back_populates="product")
    category = db.relationship("Category", back_populates="products")

class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    products = db.relationship("Product", back_populates="category")

class BasketProduct(db.Model):
    __tablename__ = "basketProducts"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    cookie_id = db.Column(db.Integer, db.ForeignKey("cookies.id"))
    amount = db.Column(db.Integer, nullable=False)
    product = db.relationship("Product", back_populates="basketProducts")
    user = db.relationship("User", back_populates="basketProducts")
    cookie = db.relationship("Cookie", back_populates="basket_products")

class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String, nullable=False)
    country = db.Column(db.String, nullable=False)
    line_1 = db.Column(db.String, nullable=False)
    line_2 = db.Column(db.String, nullable=False)
    postal_code = db.Column(db.String, nullable=False)
    body = db.Column(db.String, nullable=False)
    amount_total = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String, nullable=False)

with app.app_context():
    db.create_all()
    if not db.session.execute(db.select(User)).scalars().all():
        password = "MiskaBarmana07#"
        hash_password = generate_password_hash(password)
        new_user = User(username="Admin", email="adminKing@gmail.com", password=hash_password, permission=100)
        db.session.add(new_user)
        db.session.commit()
###########################  DATABASE ########################


###########################  LOGIN MANAGER ########################
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)
###########################  LOGIN MANAGER ########################




###########################  DECORATORS ########################
def getData(f):
    @wraps(f)
    def decorator_function(*args, **kwargs):
        logged_in = current_user.is_authenticated
        if not logged_in:
            if "user_id" not in session:
                amount = 0
            else:
                basket_products = db.session.execute(db.select(BasketProduct).where(BasketProduct.cookie_id == session["user_id"])).scalars().all()
                basket_products = [basket_products for basket_product in basket_products if basket_product.product.amount >= 1]
                amount = len(basket_products)
        else:
            basket_products = db.session.execute(db.select(BasketProduct).where(BasketProduct.user_id == current_user.id)).scalars().all()
            basket_products = [basket_products for basket_product in basket_products if basket_product.product.amount >= 1]
            amount = len(basket_products)
        kwargs['amount'] = amount
        return f(*args, **kwargs)
    return decorator_function

def adminOnly(f):
    @wraps(f)
    def decorator_function(*args, **kwargs):
        if current_user.id == 1:
            return f(*args, **kwargs)
        else:
            return abort(404)
    return decorator_function


def manageProduct(f):
    @wraps(f)
    def decorator_function(*args, **kwargs):
        if current_user.permission >= 2:
            return f(*args, **kwargs)
        else:
            return abort(404)
    return decorator_function


def seeWarehouse(f):
    @wraps(f)
    def decorator_function(*args, **kwargs):
        if current_user.permission >= 1:
            return f(*args, **kwargs)
        else:
            return abort(404)
    return decorator_function
###########################  DECORATORS ########################


###########################  INDEX PAGE ########################
@app.route("/")
@getData
def indexPage(**kwargs):
    content = {
        "logged_in": current_user.is_authenticated,
        "amount": kwargs["amount"]
    }
    return render_template("home.html", **content)
###########################  INDEX PAGE ########################



###########################  PRODUCTS ########################
@app.route("/products")
@getData
def productsPage(**kwargs):
    products = ""
    category_value = 0
    value = ""
    categories = db.session.execute(db.select(Category)).scalars().all()
    category_id = request.args.get("category")
    price = request.args.get("price")
    if price and category_id:
        category_value = int(category_id)
        if price == "1":
            value = 1
            products = db.session.execute(db.select(Product).where(Product.category_id == category_id, Product.price < 500)).scalars().all()
        elif price == "2":
            value = 2
            products = db.session.execute(db.select(Product).where(Product.category_id == category_id, Product.price >= 500, Product.price <= 1000)).scalars().all()
        elif price == "3":
            value = 3
            products = db.session.execute(db.select(Product).where(Product.category_id == category_id, Product.price > 1000, Product.price <= 5000)).scalars().all()
        elif price == "4":
            value = 4
            products = db.session.execute(db.select(Product).where(Product.category_id == category_id, Product.price > 5000)).scalars().all()
    elif category_id:
        category_value = category_id
        products = db.session.execute(db.select(Product).where(Product.category_id == category_id)).scalars().all()
    elif price:
        if price == "1":
            value = 1
            products = db.session.execute(db.select(Product).where(Product.price < 500)).scalars().all()
        elif price == "2":
            value = 2
            products = db.session.execute(db.select(Product).where(Product.price >= 500, Product.price <= 1000)).scalars().all()
        elif price == "3":
            value = 3
            products = db.session.execute(db.select(Product).where(Product.price > 1000, Product.price <= 5000)).scalars().all()
        elif price == "4":
            value = 4
            products = db.session.execute(db.select(Product).where(Product.price > 5000)).scalars().all()
    else:
        products = db.session.execute(db.select(Product)).scalars().all()

    content = {
        "logged_in": current_user.is_authenticated,
        "products": products,
        "b64encode": b64encode,
        "amount": kwargs["amount"],
        "categories": categories,
        "category_value": category_value,
        "valuee": value

    }
    return render_template("products.html", **content)
###########################  PRODUCTS ########################


###########################  ONE PRODUCT ########################
@app.route("/oneProduct/<int:num>", methods=["POST", "GET"])
@getData
def oneProduct(num, **kwargs):
    product = db.get_or_404(Product, num)
    if request.method == "POST":
        if not current_user.is_authenticated:
            if ("user_id" not in session) or not (db.session.execute(db.select(Cookie).where(Cookie.id == session["user_id"])).scalar()):
                new_cookie = Cookie()
                db.session.add(new_cookie)
                db.session.commit()
                session["user_id"] = new_cookie.id
            amount = request.form["amount"]
            basket_product = db.session.execute(db.select(BasketProduct).where(BasketProduct.product_id == num, BasketProduct.cookie_id == session["user_id"])).scalar()
            if basket_product:
                basket_product.amount = basket_product.amount + int(amount)
            else:
                cookie = db.get_or_404(Cookie, session["user_id"])
                new_basket_product = BasketProduct(cookie=cookie, product=product, amount=amount)
                db.session.add(new_basket_product)
            db.session.commit()
            return redirect(request.referrer)
        else:
            amount = request.form["amount"]
            basket_product = db.session.execute(db.select(BasketProduct).where(BasketProduct.product_id == num, BasketProduct.user_id == current_user.id)).scalar()
            if basket_product:
                basket_product.amount = basket_product.amount + int(amount)
            else:
                new_basket_product = BasketProduct(user=current_user, product=product, amount=amount)
                db.session.add(new_basket_product)
            db.session.commit()
            return redirect(request.referrer)
    content = {
        "logged_in": current_user.is_authenticated,
        "b64encode": b64encode,
        "product": product,
        "amount": kwargs["amount"]
        }
    return render_template("oneProduct.html", **content)
###########################  ONE PRODUCT ########################


###########################  BASKET ########################
@app.route("/basket")
@getData
def basketPage(**kwargs):
    logged_in = current_user.is_authenticated
    if not logged_in:
        if "user_id" not in session or not db.session.execute(db.select(Cookie).where(Cookie.id == session["user_id"])):
            new_cookie = Cookie()
            db.session.add(new_cookie)
            db.session.commit()
            session["user_id"] = new_cookie.id
        products = db.session.execute(db.select(BasketProduct).where(BasketProduct.cookie_id == session["user_id"])).scalars().all()
    else:
        products = db.session.execute(db.select(BasketProduct).where(BasketProduct.user_id == current_user.id)).scalars().all()
    products = [product for product in products if product.product.amount >= 1]
    if not products:
        content = {
            "logged_in": logged_in,
            "basket_products": products,
            "b64encode": b64encode,
            "amount": kwargs["amount"]
        }
        return render_template("emptyBasket.html", **content)
    content = {
        "logged_in": logged_in,
        "basket_products": products,
        "b64encode": b64encode,
        "amount": kwargs["amount"]
    }
    return render_template("basket.html", **content)
###########################  BASKET ########################


###########################  DELETE BASKET PRODUCT ########################
@app.route("/delete/<int:num>")
def deleteBasket(num):
    product = db.get_or_404(BasketProduct, num)
    db.session.delete(product)
    db.session.commit()
    return redirect(request.referrer)
###########################  DELETE BASKET PRODUCT ########################


###########################  ADD PRODUCT ########################
@app.route("/addProduct", methods=["POST", "GET"])
@login_required
@manageProduct
@getData
def addProduct(**kwargs):
    form = inputProduct()
    categories = db.session.execute(db.select(Category)).scalars().all()
    form.category.choices = [(category.name, category.name) for category in categories]
    if request.method == "POST":
        name = form.name.data
        description = form.description.data
        price = form.price.data
        location = form.location.data
        amount = form.amount.data
        image = form.image.data
        category = form.category.data
        image_mimetype = image.mimetype
        image = image.read()
        category = db.session.execute(db.select(Category).where(Category.name == category)).scalar()
        db.session.add(Product(name=name, description=description, price=price, image_mimetype=image_mimetype, image=image, status=0, amount=amount, location=location, category=category, owner=current_user))
        db.session.commit()
    content = {
        "logged_in": current_user.is_authenticated,
        "form": form,
        "amount": kwargs["amount"]
    }
    return render_template("addProduct.html", **content)
###########################  ADD PRODUCT ########################



###########################  ADD CATEGORY ########################
@app.route("/addCategory", methods=["GET", "POST"])
@login_required
@manageProduct
@getData
def addCategory(**kwargs):
    form = inputCategory()
    if form.validate_on_submit():
        name = form.name.data
        new_category = Category(name=name)
        db.session.add(new_category)
        db.session.commit()
    content = {
        "form": form,
        "amount": kwargs["amount"],
        "logged_in": current_user.is_authenticated
    }
    return render_template("addProduct.html", **content)
###########################  ADD CATEGORY ########################


###########################  REGISTER ########################
@app.route("/register", methods=["POST", "GET"])
@getData
def register(**kwargs):
    alerts = []
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirmPassword = request.form["confirmPassword"]
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        user_2 = db.session.execute(db.select(User).where(User.username == username)).scalar()
        if user or user_2:
            alerts.append("This user is already exist!")
        elif password != confirmPassword:
            alerts.append("Password do not match!")
        elif username == "" or email == "" or password == "":
            alerts.append("Something is empty!")
        elif not "@" in email:
            alerts.append("Email is wrong!")
        else:
            hashPassword = generate_password_hash(password, salt_length=8)
            new_user = User(username=username, email=email, password=hashPassword, permission=0)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("productsPage"))
    content = {
        "alerts": alerts,
        "logged_in": current_user.is_authenticated,
        "amount": kwargs["amount"]
    }
    return render_template("register.html", **content)
###########################  REGISTER ########################


###########################  LOGIN ########################
@app.route("/login", methods=["POST", "GET"])
@getData
def login(**kwargs):
    alert = ""
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = db.session.execute(db.Select(User).where(User.email == email)).scalar()
        if email == "" or password == "":
            alert = "Something is empty!"
        elif not user:
            alert = "This user is not exist!"
        elif check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("productsPage"))
        else:
            alert = "Wrong password"
    content = {
        "logged_in": current_user.is_authenticated,
        "alert": alert,
        "amount": kwargs["amount"]
    }
    return render_template("login.html", **content)
###########################  LOGIN ########################


###########################  LOGOUT ########################
@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('productsPage'))
###########################  LOGOUT ########################


###########################  addOneProduct ########################
@app.route("/addOne/<int:num>")
def addOne(num):
    basket_product = db.get_or_404(BasketProduct, num)
    basket_product.amount = basket_product.amount + 1
    db.session.commit()
    return redirect(request.referrer)
###########################  addOneProduct ########################


###########################  deleteOneProduct ########################
@app.route("/deleteOne/<int:num>")
def deleteOne(num):
    basket_product = db.get_or_404(BasketProduct, num)
    basket_product.amount = basket_product.amount - 1
    if basket_product.amount == 0:
        db.session.delete(basket_product)
    db.session.commit()
    return redirect(request.referrer)
###########################  deleteOneProduct ########################



###########################  DELETE BASKET PRODUCT ########################
@app.route("/deleteBasketProduct/<int:num>")
def deleteBasketProduct(num):
    basketProduct = db.get_or_404(BasketProduct, num)
    db.session.delete(basketProduct)
    db.session.commit()
    return redirect(request.referrer)
###########################  DELETE BASKET PRODUCT ########################


###########################  PAY ########################
@app.route("/pay")
@getData
def pay(**kwargs):
    logged_in = current_user.is_authenticated
    if logged_in:
        basket_products = db.session.execute(db.select(BasketProduct).where(BasketProduct.user_id == current_user.id)).scalars().all()
        if not basket_products:
            return abort(404)
    else:
        if "user_id" not in session:
            return abort(404)
        basket_products = db.session.execute(db.select(BasketProduct).where(BasketProduct.cookie_id == session["user_id"])).scalars().all()
        if not basket_products:
            return abort(404)

    for basket_product in basket_products:
        if basket_product.product.amount <= 0:
            db.session.delete(basket_product)
            basket_products.remove(basket_product)
    db.session.commit()

    try:
        line_items = []
        for basket_product in basket_products:
            x = {
                "price_data": {
                    "currency": "pln",
                    "unit_amount": basket_product.product.price*100,
                    "product_data": {
                        "name": basket_product.product.name
                    },
                },
                "quantity": basket_product.amount
            }
            line_items.append(x)
        metadata = {basket_product.product_id: basket_product.amount for basket_product in basket_products}

        checkout_session = stripe.checkout.Session.create(
            metadata=metadata,
            shipping_address_collection={"allowed_countries": ["PL"]},
            line_items=line_items,
            mode='payment',
            success_url='https://navishop.azurewebsites.net/success',
            cancel_url='https://navishop.azurewebsites.net/denied',
            automatic_tax={'enabled': True},
            locale='pl'
        )

    except stripe.error.StripeError as e:
        return str(e)
    alerts = []
    for basket_product in basket_products:
        if basket_product.product.amount < basket_product.amount:
            alerts.append(f"Brak produktu: {basket_product.product.name} na stanie w ilości {basket_product.amount}!")
    if alerts:
        return render_template("lackProduct.html", logged_in=current_user.is_authenticated, alerts=alerts, amount=kwargs["amount"])
    return redirect(checkout_session['url'], code=303)

@app.route('/webhook', methods=['POST'])
def webhook():
    event = None
    payload = request.data
    sig_header = request.headers['STRIPE_SIGNATURE']
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        raise e
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise e
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        city = event['data']['object']['shipping_details']['address']['city']
        country = event['data']['object']['shipping_details']['address']['country']
        line1 = event['data']['object']['shipping_details']['address']['line1']
        line2 = event['data']['object']['shipping_details']['address']['line2']
        postal_code = event['data']['object']['shipping_details']['address']['postal_code']
        amount_total = int(event['data']['object']['amount_total']) * 0.01
        body = ""
        metadata = event['data']['object']['metadata']
        for i in event['data']['object']['metadata']:
            product = db.get_or_404(Product, i)
            body = body + f"id={product.id} name={product.name} amount={metadata[i]}   //   "
            product.amount = product.amount - int(metadata[i])
        new_order = Order(city=city, country=country, line_1=line1, line_2=line2, postal_code=postal_code, amount_total=amount_total, body=body, status="to_implement")
        db.session.add(new_order)
        db.session.commit()
    else:
        print('Unhandled event type {}'.format(event['type']))

    return jsonify(success=True)
###########################  PAY ########################


###########################  WAREHOUSE/STORE ########################
@app.route("/warehouse")
@login_required
@seeWarehouse
@getData
def store(**kwargs):
    products = db.session.execute(db.select(Product)).scalars().all()
    content = {
        "products": products,
        "amount": kwargs["amount"],
        "logged_in": current_user.is_authenticated
    }
    return render_template("store.html", **content)
###########################  WAREHOUSE/STORE ########################


###########################  ORDERS ########################
@app.route("/orders")
@login_required
@seeWarehouse
@getData
def ordersPage(**kwargs):
    orders = db.session.execute(db.select(Order).where(Order.status == "to_implement")).scalars().all()
    content = {
        "orders": orders,
        "amount": kwargs["amount"],
        "logged_in": current_user.is_authenticated
    }
    return render_template("orders.html", **content)
###########################  ORDERS ########################


###########################  COMPLETE ORDERS ########################
@app.route("/completeOrders")
@login_required
@seeWarehouse
@getData
def completeOrdersPage(**kwargs):
    orders = db.session.execute(db.select(Order).where(Order.status == "complete")).scalars().all()
    content = {
        "orders": orders,
        "amount": kwargs["amount"],
        "logged_in": current_user.is_authenticated
    }
    return render_template("completeOrders.html", **content)
###########################  COMPLETE ORDERS ########################


###########################  EDIT PRODUCT ########################
@app.route("/editProduct/<int:num>", methods=["POST", "GET"])
@login_required
@manageProduct
@getData
def editItem(num, **kwargs):
    product = db.get_or_404(Product, num)
    categories = db.session.execute(db.select(Category)).scalars().all()
    form = editProduct(name=product.name, description=product.description, price=product.price, amount=product.amount, location=product.location, category=product.category.name)
    form.category.choices = [(category.name, category.name) for category in categories]
    if form.validate_on_submit():
        product.name = form.name.data
        product.description = form.description.data
        product.price = form.price.data
        product.amount = form.amount.data
        product.location = form.location.data
        product.category = db.session.execute(db.select(Category).where(Category.name == form.category.data)).scalar()
        if form.image.data:
            image = form.image.data
            product.image = image.read()
            product.image_mimetype = image.mimetype
        db.session.commit()
    content = {
        "form": form,
        "logged_in": current_user.is_authenticated,
        "amount": kwargs["amount"]
    }
    return render_template("addProduct.html", **content)
###########################  EDIT PRODUCT ########################


###########################  DELETE CATEGORY ########################
@app.route("/deleteCategory", methods=["POST", "GET"])
@login_required
@manageProduct
@getData
def deleteCategory(**kwargs):
    alerts = []
    categories = db.session.execute(db.select(Category)).scalars().all()
    form = deleteCategoryForm()
    form.name.choices = [(category.name, category.name) for category in categories]
    if form.validate_on_submit():
        category_name = form.name.data
        category = db.session.execute(db.select(Category).where(Category.name == category_name)).scalar()
        if category.products:
            alerts.append("You have to delete item with this category before")
        else:
            db.session.delete(category)
            db.session.commit()
            return redirect(request.referrer)
    content = {
        "form": form,
        "logged_in": current_user.is_authenticated,
        "amount": kwargs["amount"],
        "alerts": alerts
    }
    return render_template("addProduct.html", **content)
###########################  DELETE CATEGORY ########################


###########################  DELETE ITEM ########################
@app.route("/deleteItem/<int:num>")
@login_required
@manageProduct
def deleteItem(num):
    item = db.get_or_404(Product, num)
    basket_products = db.session.execute(db.select(BasketProduct).where(BasketProduct.product_id == item.id)).scalars().all()
    for basket_product in basket_products:
        db.session.delete(basket_product)
    db.session.delete(item)
    db.session.commit()
    return redirect(request.referrer)
###########################  DELETE ITEM ########################


###########################  IMPLEMENT ORDER ########################
@app.route("/implementOrder/<int:num>")
@login_required
@manageProduct
def implementOder(num):
    order = db.get_or_404(Order, num)
    order.status = "complete"
    db.session.commit()
    return redirect(request.referrer)
###########################  IMPLEMENT ORDER ########################


###########################  SUCCESS PAGE ########################
@app.route("/success")
@getData
def successPage(**kwargs):
    if not "user_id" in session:
        return abort(404)
    if not current_user.is_authenticated:
        basket_products = db.session.execute(db.select(BasketProduct).where(BasketProduct.cookie_id == session["user_id"])).scalars().all()
    else:
        basket_products = db.session.execute(db.select(BasketProduct).where(BasketProduct.user_id == current_user.id)).scalars().all()
    if basket_products:
        for basket_product in basket_products:
            db.session.delete(basket_product)
        db.session.commit()
        return redirect(url_for("successPage"))
    content = {
        "logged_in": current_user.is_authenticated,
        "amount": kwargs["amount"]
    }
    return render_template("success.html", **content)
###########################  SUCCESS PAGE ########################


###########################  DENIED PAGE ########################
@app.route("/denied")
@getData
def denyPage(**kwargs):
    content = {
        "logged_in": current_user.is_authenticated,
        "amount": kwargs["amount"]
    }
    return render_template("denied.html", **content)
###########################  DENIED PAGE ########################



if __name__  == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(3000))

