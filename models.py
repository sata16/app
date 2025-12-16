from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import date, datetime

db = SQLAlchemy()

# === Пользователи (для входа) ===
class User(UserMixin, db.Model):
    __tablename__ = 'users'  # у тебя в БД таблица users

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.username}>"


# === Клиенты (арендаторы) ===
class Client(db.Model):
    __tablename__ = 'client'

    client_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50))
    notes = db.Column(db.Text, nullable=True)

    bookings = db.relationship('Booking', back_populates='client', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Client {self.name}>"


# === Парковки ===
class Parking(db.Model):
    __tablename__ = 'parking'

    parking_id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(200), nullable=False)
    spots = db.relationship('ParkingSpot', back_populates='parking', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Parking {self.address}>"


# === Парковочные места ===
class ParkingSpot(db.Model):
    __tablename__ = 'parking_spot'

    spot_id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), nullable=False)
    parking_id = db.Column(db.Integer, db.ForeignKey('parking.parking_id', ondelete='CASCADE'))
    status = db.Column(db.String(50), default='свободно')
    parking = db.relationship('Parking', back_populates='spots')
    bookings = db.relationship('Booking', back_populates='spot', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Spot {self.number} ({self.parking.address if self.parking else '—'})>"


# === Бронирования ===
class Booking(db.Model):
    __tablename__ = 'booking'

    booking_id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    cost = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(50), default='активно')
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.spot_id', ondelete='CASCADE'))
    client_id = db.Column(db.Integer, db.ForeignKey('client.client_id', ondelete='CASCADE'))
    utilities = db.Column(db.Numeric(10, 2))
    rent_size = db.Column(db.Numeric(10, 2))
    notes = db.Column(db.Text)
    

    spot = db.relationship('ParkingSpot', back_populates='bookings')
    client = db.relationship('Client', back_populates='bookings')
    payments = db.relationship('Payment', back_populates='booking', cascade="all, delete-orphan")
    expenses = db.relationship('Expense', back_populates='booking', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Booking {self.booking_id} — {self.status}>"

    @property
    def total_amount(self):
        rent = float(self.rent_size or 0)
        utils = float(self.utilities or 0)
        return rent + utils


# === Платежи ===
class Payment(db.Model):
    __tablename__ = 'payment'

    payment_id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.Date, default=date.today)
    method = db.Column(db.String(30), default='онлайн')
    status = db.Column(db.String(20), default='оплачено')
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.booking_id', ondelete='CASCADE'))

    booking = db.relationship('Booking', back_populates='payments')

    def __repr__(self):
        return f"<Payment {self.payment_id}: {self.amount}>"


# === Расходы (привязаны к аренде) ===
class Expense(db.Model):
    __tablename__ = 'expense'

    expense_id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.booking_id', ondelete='CASCADE'))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255))
    expense_date = db.Column(db.Date, default=date.today)

    booking = db.relationship('Booking', back_populates='expenses')

    def __repr__(self):
        return f"<Expense {self.expense_id}: {self.amount}>"