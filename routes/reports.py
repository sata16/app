# app/routes/reports.py

from flask import Blueprint, render_template, request, flash
from flask_login import login_required
from models import db, Payment, Booking, Parking, ParkingSpot, Client
from datetime import datetime
from decimal import Decimal

bp = Blueprint('reports', __name__, url_prefix='/reports')


# ================================
# ЕДИНАЯ СТРАНИЦА С ОТЧЁТОМ
# ================================
@bp.route('/view', methods=['GET'])
@login_required
def view():
    report_type = request.args.get('type')
    start = request.args.get('start')
    end = request.args.get('end')
    parking_id = request.args.get('parking_id', type=int)

    parkings = Parking.query.order_by(Parking.address).all()

    # если выбран только тип отчёта, но без периода → отчёт не формируем
    if report_type and not (start and end):
        return render_template(
            'reports.html',
            report_type=report_type,
            report_data=None,
            parkings=parkings
        )

    # если тип отчёта не выбран
    if not report_type:
        return render_template(
            'reports.html',
            report_type=None,
            report_data=None,
            parkings=parkings
        )

    # обработка дат
    try:
        start_date = datetime.strptime(start, '%Y-%m-%d')
        end_date = datetime.strptime(end, '%Y-%m-%d')
    except:
        flash("Некорректный формат даты", "danger")
        return render_template(
            'reports.html',
            report_type=report_type,
            report_data=None,
            parkings=parkings
        )

    # формируем нужный отчёт
    if report_type == 'payments':
        data = get_payments(start_date, end_date, parking_id)
    elif report_type == 'charges':
        data = get_charges(start_date, end_date, parking_id)
    elif report_type == 'finance':
        data = get_finance(start_date, end_date, parking_id)
    else:
        data = None

    return render_template(
        'reports.html',
        report_type=report_type,
        report_data=data,
        parkings=parkings
    )

# ================================
#   ФУНКЦИИ ФОРМИРОВАНИЯ ОТЧЁТОВ
# ================================

def get_payments(start_date, end_date, parking_id):
    """Отчёт по платежам"""
    query = Payment.query.join(Booking).join(ParkingSpot).join(Parking)

    if start_date:
        query = query.filter(Payment.payment_date >= start_date)
    if end_date:
        query = query.filter(Payment.payment_date <= end_date)
    if parking_id:
        query = query.filter(Parking.parking_id == parking_id)

    rows = query.order_by(Payment.payment_date).all()

    table = {
        "columns": ["Дата", "Арендатор", "Парковка", "Сумма"],
        "rows": []
    }

    for p in rows:
        table["rows"].append([
            p.payment_date.strftime("%d.%m.%Y"),
            p.booking.client.name if p.booking.client else "—",
            p.booking.spot.parking.address if p.booking.spot else "—",
            f"{p.amount:.2f}"
        ])

    return table


def get_charges(start_date, end_date, parking_id):
    """Отчёт по начислениям"""
    query = Booking.query.join(ParkingSpot).join(Parking)

    if start_date:
        query = query.filter(Booking.start_date >= start_date)
    if end_date:
        query = query.filter(Booking.end_date <= end_date)
    if parking_id:
        query = query.filter(Parking.parking_id == parking_id)

    rows = query.order_by(Booking.start_date).all()

    table = {
        "columns": ["Период", "Арендатор", "Парковка", "Начислено"],
        "rows": []
    }

    for b in rows:
        period = f"{b.start_date.strftime('%d.%m.%Y')} — {b.end_date.strftime('%d.%m.%Y')}"
        table["rows"].append([
            period,
            b.client.name if b.client else "—",
            b.spot.parking.address if b.spot else "—",
            f"{(b.rent_size or 0):.2f}"
        ])

    return table


def get_finance(start_date, end_date, parking_id):
    """Финансовый отчёт: начислено – оплачено"""

    # --- получаем бронирования (начисления) ---
    b_query = Booking.query.join(ParkingSpot).join(Parking)

    if start_date:
        b_query = b_query.filter(Booking.start_date >= start_date)
    if end_date:
        b_query = b_query.filter(Booking.end_date <= end_date)
    if parking_id:
        b_query = b_query.filter(Parking.parking_id == parking_id)

    bookings = b_query.all()

    rows = []
    total_charged = 0
    total_paid = 0

    for b in bookings:
        charged = b.rent_size or 0  # начислено

        # сумма платежей по этому бронированию
        paid = sum(p.amount for p in b.payments) if b.payments else 0

        balance = charged - paid

        total_charged += charged
        total_paid += paid

        rows.append([
            f"{b.start_date.strftime('%d.%m.%Y')} — {b.end_date.strftime('%d.%m.%Y')}",
            b.client.name if b.client else "—",
            b.spot.parking.address if b.spot else "—",
            f"{charged:.2f}",
            f"{paid:.2f}",
            f"{balance:.2f}"
        ])

    return {
        "columns": ["Период", "Арендатор", "Адрес", "Начислено", "Оплачено", "Остаток"],
        "rows": rows,
        "total_charged": f"{total_charged:.2f}",
        "total_paid": f"{total_paid:.2f}",
        "total_balance": f"{(total_charged - total_paid):.2f}",
    }