import os
import logging
import queries
from cart import Cart
from create_fake_accounts import create_fake_db_accounts
from werkzeug.utils import secure_filename
from flask import Flask, redirect, render_template, request, session, url_for, flash, abort
from models import Chat, Product
from models import db
from models import Chat, Message, User, Tag
from datetime import datetime
from flask import request, session, jsonify
from models import User  # убедись, что импортировал User
from models import create_tables
from models import Deal
from ton_payment import find_transaction
from ton_escrow import send_ton  # Импорт твоей функции отправки TON
import os
from werkzeug.utils import secure_filename
import uuid
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    filename="application.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(message)s",
)


app = Flask(__name__)
app.secret_key = os.urandom(16)

#create_fake_db_accounts()  # comment out this line after db initialised


@app.route('/')
def frontpage():
    featured_products = queries.get_newest_products()
    return render_template("home_page.html", products=featured_products)


@app.route('/home/')
def home():
    return redirect(url_for("frontpage"))

UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/sign_out/')
def logout():
    if "user" in session:
        session.pop("user", None)
        flash("You have been signed out", 'info')
    return redirect(url_for("frontpage"))


@app.route('/my_profile/')
def my_profile():
    if "user" in session:
        user = session["user"]
        user_products = queries.list_user_products(user["user_id"])
        user_sales = queries.list_user_sales(user["user_id"])
        user_purchases = queries.list_user_purchases(user["user_id"])
        return render_template('my_profile.html', user=user, products=user_products[:7], sales=user_sales[:7], purchases=user_purchases[:7])
    else:  # user must be logged in
        return redirect(url_for('login'))


@app.route('/my_profile/edit_profile/', methods=['GET', 'POST'])
def edit_profile():
    if "user" not in session:
        return redirect(url_for('login'))

    user = session["user"]

    if request.method == "POST":
        name = request.form.get("full_name", "")
        address = request.form.get("address", "")
        bio = request.form.get("bio", "")

        # Получаем загруженный файл
        avatar_file = request.files.get("avatar_file")
        avatar_url = user["avatar_url"]  # по умолчанию — старый URL

        if avatar_file and avatar_file.filename:
            filename = avatar_file.filename
            save_path = os.path.join("static", "uploads", filename)

            # Создаем папку при необходимости
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            avatar_file.save(save_path)
            avatar_url = "/" + save_path.replace("\\", "/")  # для HTML src

        # Сохраняем в базу
        updated_user = queries.edit_user(
            user["user_id"], name, address, bio, avatar_url
        )

        if updated_user:
            session["user"] = updated_user
            session.modified = True
            return redirect(url_for('my_profile'))
        else:
            flash("Something went wrong. Couldn't update your profile", 'error')
            return redirect(url_for('edit_profile'))

    # GET-запрос
    return render_template("edit_profile.html", user=user)

@app.route('/my_profile/add_product/', methods=['GET', 'POST'])
def add_product():
    all_tags = list(Tag.select())  # передаём список объектов, а не строк

    if "user" not in session:
        return redirect(url_for('login'))

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        price = request.form.get("price")
        qty = request.form.get("qty")
        tag_list = request.form.getlist("tags")  # 🟢 изменено здесь
        user = session["user"]

        product = {
            "title": title,
            "description": description,
            "price_in_cents": float(price) * 100,
            "qty": int(qty),
            "vendor": user
        }

        product_id = queries.add_product_to_catalog(product)

        if product_id:
            # Загружаем изображения
            image_fields = ["image_1", "image_2", "image_3", "image_4", "image_5"]
            image_urls = []

            for field in image_fields:
                file = request.files.get(field)
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    save_path = os.path.join("static", "uploads", filename)
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    file.save(save_path)
                    image_urls.append("/" + save_path.replace("\\", "/"))

            if image_urls:
                queries.add_images_to_product(product_id, image_urls)

            # Добавляем выбранные теги
            if tag_list:
                queries.add_product_tags(product_id, tag_list)

            return redirect(url_for("product_page", product_id=product_id))
        else:
            flash("Could not add product", 'error')
            return redirect(url_for('add_product'))

    return render_template("add_product.html", all_tags=all_tags)




@app.route('/my_profile/edit_product/<product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if "user" in session:
        if request.method == "POST":

            # get updated product info from form
            title = request.form["title"]
            description = request.form["description"]
            price = request.form["price"]
            qty = request.form["qty"]
            thumbnail = request.form["thumbnail"]

            edit_successful = queries.edit_product(
                product_id, title, description, price, qty, thumbnail)

            if edit_successful:
                return redirect(url_for("my_products"))
            else:
                flash("Something went wrong. Couldn't update product", 'error')
                return redirect(url_for("edit_product", product_id=product_id, _method='GET'))

        else:  # request.method == "GET"
            product = queries.get_product(product_id)
            if product:
                return render_template("edit_product.html", product=product)
            else:
                abort(404)
    else:  # user must be logged in
        return redirect(url_for('login'))


@app.route('/my_profile/remove_product/<product_id>')
def remove_product(product_id):
    if "user" in session:
        user = session["user"]

        product_was_removed = queries.remove_product(
            user["user_id"], product_id)

        if product_was_removed:
            flash("Product has been removed", 'info')
        else:
            flash("Could not remove product", 'error')
        return redirect(url_for("my_products"))
    else:  # user must be logged in
        return redirect(url_for('login'))


@app.route('/my_profile/my_products/')
def my_products():
    if "user" in session:
        user = session["user"]
        products = queries.list_user_products(user["user_id"])
        return render_template("my_products.html", products=products)
    else:  # user must be logged in
        return redirect(url_for('login'))


@app.route('/my_profile/my_sales/')
def my_sales():
    if "user" in session:
        user = session["user"]
        sales = queries.list_user_sales(user["user_id"])
        return render_template("my_sales.html", sales=sales)
    else:  # user must be logged in
        return redirect(url_for('login'))


@app.route('/my_profile/my_purchases/')
def my_purchases():
    if "user" in session:
        user = session["user"]
        purchases = queries.list_user_purchases(user["user_id"])
        return render_template("my_purchases.html", purchases=purchases)
    else:  # user must be logged in
        return redirect(url_for('login'))


@app.route('/user_page/<username>')
def user_page(username):
    ellipsis_user = queries.get_user(username)
    if ellipsis_user:
        user_products = queries.list_user_products(ellipsis_user['user_id'])
        return render_template("user_page.html", ellipsis_user=ellipsis_user, products=user_products)
    else:
        abort(404)


@app.route('/product_page/<product_id>', methods=['GET', 'POST'])
def product_page(product_id):
    if request.method == "POST":  # product added to cart
        cart = Cart(session)

        # get product and quantity
        quantity = int(request.form["quantity"])
        user_cart = cart.add_product(
            product_id, quantity)  # returns a cart dict

        # update cart in session
        session['cart'] = user_cart
        session.modified = True
        flash("Item added to cart", 'info')

        return redirect(url_for("product_page", product_id=product_id, _method='GET'))
    else:  # request.method == "GET"
        product = queries.get_product(product_id)
        if product:  # if product exists
            product_tags = queries.get_product_tags(product_id)
            product_images = queries.get_product_images(product_id)
            return render_template("product_page.html", product=product, product_images=product_images, product_tags=product_tags)
        else:
            abort(404)


@app.route('/products/')
def all_products():
    products = queries.get_all_products()
    return render_template("products_page.html", query='All Products', products=products)


@app.route('/products/<tag>')
def search_products_by_tag(tag):
    tagged_products = queries.list_products_per_tag(tag)
    return render_template("products_page.html", query=tag, products=tagged_products)


@app.route('/products/search/')
def search_products():
    query = request.args.get("query")
    products = queries.search(query)
    return render_template("products_page.html", query=query, products=products)


@app.route('/view_cart/', methods=['GET', 'POST'])
def view_cart():
    if "user" not in session:
        flash("you must be logged in to view your cart", 'error')
        return redirect(url_for('login'))

    cart = Cart(session)

    if request.method == "POST":
        buyer_id = session["user"]['user_id']
        if queries.checkout(buyer_id, cart):
            session.pop("cart", None)

            from models import Chat, Product, Deal
            import uuid
            from datetime import datetime

            buyer = session["user"]
            last_purchase = queries.get_last_user_purchase(buyer["user_id"])
            product = last_purchase.product
            seller = last_purchase.vendor

            # 🆕 создаём короткий код сделки
            deal_code = f"deal_{uuid.uuid4().hex[:6]}"

            # 🆕 создаём новый чат (всегда)
            chat = Chat.create(
                buyer=buyer["user_id"],
                seller=seller.user_id,
                product=product.prod_id,
                deal_code=deal_code
            )

            # 🆕 создаём сделку и связываем с чатом
            deal = Deal.create(
                chat=chat,
                code=deal_code,  # используем тот же код
                amount_ton=product.price_in_cents / 100,
                status="awaiting_payment",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            logging.info(
                "Deal created: code=%s chat=%s buyer=%s seller=%s amount=%s",
                deal_code,
                chat.chat_id,
                buyer["user_id"],
                seller.user_id,
                product.price_in_cents / 100,
            )

            return redirect(url_for('chat_view', chat_id=chat.chat_id))
        else:
            flash("Something went wrong, could not place your order", 'error')
            return redirect(url_for('view_cart'))

    else:  # GET
        remove_cart_item = request.args.get('remove_from_cart', '')
        update_item_qty = request.args.get('change_quantity', '')
        quantity = int(request.args.get('quantity', 0))

        if remove_cart_item:
            session['cart'] = cart.remove_product(remove_cart_item)
            session.modified = True
            return redirect(url_for('view_cart'))

        if update_item_qty:
            session['cart'] = cart.add_product(update_item_qty, quantity)
            session.modified = True
            return redirect(url_for('view_cart'))

        return render_template('cart.html', cart=cart)

    

@app.route('/chat/<int:chat_id>', methods=['GET', 'POST'])
def chat_view(chat_id):
    chat = Chat.get_or_none(Chat.chat_id == chat_id)
    if not chat:
        abort(404)

    user = session.get("user")
    if not user or user["user_id"] not in [chat.buyer.user_id, chat.seller.user_id]:
        abort(403)

    # 🔽 Генерация ссылки на оплату
    GUARANTOR_ADDRESS = "UQAWnYHtT4X8bZImSMppdhE2GAqTwS-yLVaz_ry-wSM6RFDr"  # заменишь на свой
    amount = chat.product.price_in_cents*10000000
    payment_url = f"ton://transfer/{GUARANTOR_ADDRESS}?amount={amount}&text={chat.deal_code}"


    Message.update(is_read=True).where(
        (Message.chat == chat) &
        (Message.sender != user["user_id"]) &
        (Message.is_read == False)
    ).execute()

    if request.method == "POST":
        content = request.form.get("message", "").strip()
        if content:
            Message.create(
                chat=chat,
                sender=user["user_id"],
                content=content,
                timestamp=datetime.now()
            )
            logging.info(
                "Chat message: chat=%s sender=%s", chat.chat_id, user["user_id"]
            )

    messages = Message.select().where(Message.chat == chat).order_by(Message.timestamp)
    deal = Deal.get_or_none(Deal.chat == chat)  
    return render_template("chat.html", chat=chat, messages=messages, current_user_id=user["user_id"], deal=deal, payment_url=payment_url)

@app.route('/check_payment/<int:chat_id>', methods=['POST'])
def check_payment(chat_id):
    chat = Chat.get_or_none(Chat.chat_id == chat_id)
    deal = Deal.get_or_none(Deal.chat == chat)
    if not chat:
        abort(404)

    buyer_wallet = chat.buyer.wallet_address
    deal_comment = chat.deal_code  # это поле мы добавили в Chat

    is_paid = find_transaction(buyer_wallet, deal_comment)
    if is_paid:
        deal.status = "paid"
        deal.updated_at = datetime.now()
        deal.save()
        logging.info("Deal %s marked as paid", deal.code)
        flash("✅ Оплата найдена в блокчейне", "success")
    else:
        flash("❌ Оплата не найдена. Попробуйте позже", "error")
        
    return redirect(url_for("chat_view", chat_id=chat_id))

@app.route('/confirm_delivery/<int:chat_id>', methods=['POST'])
def confirm_delivery(chat_id):
    if "user" not in session:
        flash("Войдите в аккаунт", "warning")
        return redirect(url_for("login"))

    user_id = session["user"]["user_id"]
    chat = Chat.get_or_none(Chat.chat_id == chat_id)

    if not chat or chat.buyer.user_id != user_id:
        abort(403)

    deal = Deal.get_or_none(Deal.chat == chat)

    if not deal or deal.status != "shipped":
        flash("Сделку нельзя подтвердить", "danger")
        return redirect(url_for("chat_view", chat_id=chat_id))

    try:
        recipient = chat.seller.wallet_address
        tx_hash = send_ton(recipient, deal.amount_ton, chat.deal_code)

        deal.status = "finished"
        deal.updated_at = datetime.now()
        deal.save()
        logging.info("Deal %s marked as finished", deal.code)

        flash(f"✅ Оплата продавцу завершена. Хеш транзакции: {tx_hash}", "success")
    except Exception as e:
        flash(f"Ошибка при переводе TON: {str(e)}", "danger")

        Message.create(
            chat=chat,
            sender=None,  # или None
            content="СДЕЛКА УСПЕШНО ЗАВЕРШЕНА, ЧАТ ЗАКРЫТ",
            is_system=True,
        )
        logging.info("System message in chat %s: deal finished", chat.chat_id)

    chat.is_active = False
    chat.save()
    logging.info("Chat %s closed", chat.chat_id)


    return redirect(url_for("rate_seller", deal_id=deal.deal_id))

@app.route('/mark_shipped/<int:deal_id>', methods=['POST'])
def mark_shipped(deal_id):
    deal = Deal.get_or_none(Deal.deal_id == deal_id)
    if not deal:
        return "Сделка не найдена", 404

    if deal.status != "paid":
        return "Сделка ещё не оплачена", 400

    deal.status = "shipped"
    deal.updated_at = datetime.now()
    deal.save()
    logging.info("Deal %s marked as shipped", deal.code)
    return redirect(request.referrer or url_for('seller_dashboard'))


@app.route('/rate_seller/<int:deal_id>', methods=['GET', 'POST'])
def rate_seller(deal_id):
    if "user" not in session:
        return redirect(url_for('login'))

    deal = Deal.get_or_none(Deal.deal_id == deal_id)
    if not deal:
        abort(404)

    if session["user"]["user_id"] != deal.chat.buyer.user_id:
        abort(403)

    seller = deal.chat.seller

    if request.method == "POST":
        try:
            rating = int(request.form.get("rating", 0))
        except ValueError:
            rating = 0

        if rating < 1 or rating > 5:
            flash("Оценка должна быть от 1 до 5", "danger")
            return redirect(url_for("rate_seller", deal_id=deal_id))

        seller.rating_total += rating
        seller.rating_count += 1
        seller.save()
        flash("Спасибо за вашу оценку!", "success")
        return redirect(url_for("frontpage"))

    return render_template("rate_seller.html", seller=seller)

@app.route('/my_chats/')
def my_chats():
    if "user" not in session:
        return redirect(url_for("login"))

    user_id = session["user"]["user_id"]

    from models import Chat

    chats = Chat.select().where(
        (Chat.buyer == user_id) | (Chat.seller == user_id)
    ).order_by(Chat.chat_id.desc())

    return render_template("my_chats.html", chats=chats, current_user_id=user_id)

@app.route("/login_wallet", methods=["POST"])
def login_wallet():
    data = request.get_json()
    address = data.get("address")

    if not address:
        return jsonify({"success": False, "error": "No wallet address"}), 400

    # Создаём или находим пользователя
    user, created = User.get_or_create(wallet_address=address)

    session["user"] = {
        "user_id": user.user_id,
        "wallet_address": user.wallet_address,
        "full_name": user.full_name or "",
        "address": user.address or "",
        "bio": user.bio or "",
        "avatar_url": user.avatar_url or "",
        "rating_total": user.rating_total,
        "rating_count": user.rating_count
    }

    return jsonify({"success": True, "new_user": created})


@app.context_processor
def inject_unread_chat_count():
    if "user" in session:
        user_id = session["user"]["user_id"]
        from queries import count_unread_chats
        unread_count = count_unread_chats(user_id)
        return dict(unread_chats=unread_count)
    return dict(unread_chats=0)


@app.route('/checkout/success/')
def success():
    return render_template('success.html')


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.before_request
def before_request():
    if db.is_closed():
        db.connect()

@app.teardown_request
def teardown_request(exception):
    if not db.is_closed():
        db.close()

create_tables()

if __name__ == "__main__":
    app.run(debug=True)
