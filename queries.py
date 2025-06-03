__winc_id__ = "d7b474e9b3a54d23bca54879a4f1855b"
__human_name__ = "ellipsis Webshop"

import peewee
from peewee import fn
from flask import flash
from playhouse.shortcuts import model_to_dict
from models import User, Product, Transaction, ProductImage, Tag, Message, Chat

def get_user_by_wallet(wallet_address):
    try:
        user = User.get(User.wallet_address == wallet_address)
        return model_to_dict(user)
    except peewee.DoesNotExist:
        return False
    
def user_to_dict(user):
    return {
        "user_id": user.user_id,
        "wallet_address": user.wallet_address,
        "full_name": user.full_name or "",
        "address": user.address or "",
        "bio": user.bio or "",
        "avatar_url": user.avatar_url or ""
    }



def edit_user(user_id, name, address, bio, avatar_url):
    try:
        user = User.get_by_id(user_id)

        if name:
            user.full_name = name
        if address:
            user.address = address
        if bio:
            user.bio = bio
        if avatar_url:
            user.avatar_url = avatar_url

        user.save()
        return user_to_dict(user)
    except peewee.PeeweeException:
        return False



def add_product_to_catalog(product_info):
    '''creates and adds a product to user's profile'''
    try:
        user = User.get_by_id(product_info['vendor']['user_id'])

        product = Product.create(title=product_info["title"], description=product_info['description'],
                                 price_in_cents=product_info['price_in_cents'], qty=product_info['qty'], vendor=user)
        # product.save()
        return product.prod_id
    except peewee.PeeweeException:
        return False


def add_images_to_product(product_id, image_list):
    '''adds list of images to a product'''
    product = Product.get_by_id(product_id)

    # set first image as product thumbnail
    product.thumbnail = image_list[0]
    product.save()

    for image_url in image_list:
        if image_url:  # if image field isn't empty
            prod_image = ProductImage(product=product, image_url=image_url)
            prod_image.save()


def add_product_tags(product_id, tag_list):
    '''adds tags to a product'''
    product = Product.get_by_id(product_id)

    for tag in tag_list:
        if tag:
            Tag.get_or_create(name=tag.lower())
            product.tags.add(Tag.get(Tag.name == tag.lower()))


def edit_product(product_id, title, description, price, qty, thumbnail):
    '''modifies and updates a product info'''
    # note to docent: this function replaces the update_stock function from the Winc assignment
    try:
        product = Product.get_by_id(product_id)

        if title:
            product.title = title
        if description:
            product.description = description
        if price:
            product.price_in_cents = float(price) * 100
        if qty:
            product.qty = int(qty)
        if thumbnail:
            product.thumbnail = thumbnail

        product.save()
        return model_to_dict(product)
    except peewee.PeeweeException:
        return False


def remove_product(user_id, product_id):
    '''removes a product from database'''
    try:
        user = User.get_by_id(user_id)
        product = Product.get_by_id(product_id)

        # ensure user deleting product is product's vendor
        if user == product.vendor:
            product_deleted = product.delete_instance()
            return product_deleted
        else:
            return False
    except peewee.IntegrityError:
        flash("Could not remove product.", 'error')
        return False

def get_last_user_purchase(user_id):
    return (Transaction
            .select()
            .where(Transaction.buyer == user_id)
            .order_by(Transaction.date.desc())
            .get())

def get_product(product_id):
    '''finds and returns a product dictionary from database'''
    try:
        product = Product.get_by_id(product_id)
        return model_to_dict(product, backrefs=True)
    except peewee.DoesNotExist:
        return False


def get_product_images(product_id):
    '''returns a list of product_images if any'''
    product = Product.get_by_id(product_id)
    images = [image.image_url for image in product.images]
    return images


def get_product_tags(product_id):
    '''returns a list of tags associated to a product if any'''
    product = Product.get_by_id(product_id)
    tags = [tag.name for tag in product.tags]
    return tags


def get_newest_products():
    query = (Product
             .select()
             .order_by(Product.prod_id.desc())
             .limit(12))
    
    products = []
    for product in query:
        data = model_to_dict(product, backrefs=True)
        data['tags'] = [tag.name for tag in product.tags]
        products.append(data)
    return products




def get_all_products():
    '''returns all products from database'''
    query = Product.select()
    products = [model_to_dict(product, backrefs=True) for product in query]
    return products


def list_user_products(user_id):
    '''returns a list of products a user is selling'''
    user = User.get_by_id(user_id)
    products = [model_to_dict(product, backrefs=True)
                for product in user.products]
    return products


def list_user_sales(user_id):
    '''returns a list of sales for a given user'''
    user = User.get_by_id(user_id)
    sales = [model_to_dict(sale, backrefs=True) for sale in user.sales]
    return sales


def list_user_purchases(user_id):
    '''returns a list of purchases made by a given user'''
    user = User.get_by_id(user_id)
    purchases = [model_to_dict(purchase, backrefs=True)
                 for purchase in user.purchases]
    return purchases


def list_products_per_tag(tag_name):
    '''returns a list of products associated with a given tag'''
    tag = Tag.get(Tag.name == tag_name)
    products = [model_to_dict(product) for product in tag.products]
    return products


def search(term):
    '''returns a list of products whose name or description contains a given term'''
    search_term = term.lower()
    query = (Product
             .select()
             .where(fn.Lower(Product.title).contains(search_term) | fn.Lower(Product.description).contains(search_term)))
    products = [model_to_dict(product) for product in query]
    return products

def get_last_user_purchase(user_id):
    return (Transaction
            .select()
            .where(Transaction.buyer == user_id)
            .order_by(Transaction.date.desc())
            .get())  # .get() выбрасывает ошибку, если ничего нет — это нормально

def count_unread_chats(user_id):
    unread_chat_ids = (Message
        .select(Message.chat)
        .join(Chat)
        .where(
            (Message.is_read == False) &
            (Message.sender != user_id) &
            ((Chat.buyer == user_id) | (Chat.seller == user_id))
        )
        .distinct())
    return unread_chat_ids.count()


def checkout(buyer_id, cart):
    '''adds purchase info to transactions database'''
    # note to docent: this function replaces the purchase_product function from the Winc assignment
    try:
        buyer = User.get_by_id(buyer_id)
        for item in cart:
            quantity = item['quantity']
            product = Product.get_by_id(item['id'])
            vendor = product.vendor

            if product.qty > quantity:
                Transaction.create(
                    vendor=vendor,
                    buyer=buyer,
                    product=product,
                    qty=quantity,
                    product_thumb_url=product.thumbnail,
                    prod_title=product.title,
                    buyer_name=buyer.full_name or "Покупатель",
                    vendor_name=vendor.full_name or "Продавец"
                )

                product.qty -= quantity
                product.save()
            else:
                flash(
                    f"Could not order '{product.title}'. Not enough in stock", 'error')
        return True
    except peewee.PeeweeException:
        return False
