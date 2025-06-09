import os
from peewee import *
from datetime import date, datetime
from peewee import PostgresqlDatabase
from dotenv import load_dotenv

# Ensure database "ellipsis.db" is created in current folder
load_dotenv("local.env")

full_path = os.path.realpath(__file__)
file_dir = os.path.dirname(full_path)
db_path = os.path.join(file_dir, 'ellipsis.db')

print("DB_PORT:", os.getenv("DB_PORT"))


db = PostgresqlDatabase(
    os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT'))
)
# Pragmas ensure foreign-key constraints are enforced.


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    user_id = AutoField()
    wallet_address = CharField(unique=True)
    full_name = CharField(null=True, default="")        # <== ОБЯЗАТЕЛЬНО
    address = CharField(null=True)          # <== ОБЯЗАТЕЛЬНО
    bio = TextField(null=True)
    avatar_url = CharField(null=True)
    rating_total = FloatField(default=0)
    rating_count = IntegerField(default=0)

class Tag(BaseModel):
    tag_id = AutoField()
    name = CharField(max_length=50, unique=True)

class Product(BaseModel):
    prod_id = AutoField()
    vendor = ForeignKeyField(User, backref='products', on_delete='CASCADE')
    title = CharField(max_length=100)
    qty = IntegerField(constraints=[Check('qty >= 0')])
    price_in_cents = IntegerField(constraints=[Check('price_in_cents >= 0')])
    description = TextField(null=True)
    thumbnail = CharField(null=True)
    date_added = DateField(default=date.today())
    tags = ManyToManyField(Tag, backref='products', on_delete='CASCADE')


class Transaction(BaseModel):   
    trans_id = AutoField()
    vendor = ForeignKeyField(User, backref='sales',
                             on_delete='SET NULL', null=True)
    buyer = ForeignKeyField(User, backref='purchases',
                            on_delete='SET NULL', null=True)
    product = ForeignKeyField(
        Product, backref='orders', on_delete='SET NULL', null=True)
    qty = IntegerField(constraints=[Check('qty > 0')])
    date = DateField(default=date.today())
    # if product or user is modified or deleted from db we should still
    # be able to view some of their info in (existing) orders
    # by storing them as order details (below)
    product_thumb_url = CharField(null=True)
    prod_title = CharField(max_length=100)
    buyer_name = CharField(max_length=100)
    vendor_name = CharField(max_length=100)


class ProductImage(BaseModel):
    img_id = AutoField()
    product = ForeignKeyField(Product, backref='images', on_delete='CASCADE')
    image_url = CharField()


class Chat(BaseModel):
    chat_id = AutoField()
    buyer = ForeignKeyField(User, backref='chats_as_buyer', on_delete='CASCADE')
    seller = ForeignKeyField(User, backref='chats_as_seller', on_delete='CASCADE')
    product = ForeignKeyField(Product, backref='chats', on_delete='CASCADE')
    is_active = BooleanField(default=True)
    deal_code = CharField(null=True)  # ← новое поле


class Message(BaseModel):
    msg_id = AutoField()
    chat = ForeignKeyField(Chat, backref='messages', on_delete='CASCADE')
    sender = ForeignKeyField(User, backref='sent_messages', on_delete='CASCADE')
    content = TextField()
    timestamp = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])
    is_read = BooleanField(default=False)
    is_system = BooleanField(default=False)

class Deal(BaseModel):
    deal_id = AutoField()
    chat = ForeignKeyField(Chat, backref="deal", unique=True)
    code = CharField(unique=True)  # уникальный код сделки (для комментария)
    amount_ton = FloatField()      # сумма сделки
    status = CharField(default="awaiting_payment")  # например: awaiting_payment, paid, shipped, confirmed, finished
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)


ProductTag = Product.tags.get_through_model()


def create_tables():
    with db:
        db.create_tables([User, Product, Transaction,
                  ProductImage, Tag, ProductTag,
                  Chat, Message, Deal])
