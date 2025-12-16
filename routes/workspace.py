# app/routes/workspace.py
from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy.orm import joinedload
from models import db, Parking, ParkingSpot, Booking, Client, Payment

bp = Blueprint('workspace', __name__, url_prefix='/workspace')


# ================================================================
#   ШАХМАТКА
# ================================================================
@bp.route('/', methods=['GET'])
@login_required
def view():
    selected_parking_id = request.args.get('parking_id', type=int)
    year_offset = request.args.get('year_offset', type=int, default=0)

    today = date.today()
    target_year = today.year + year_offset

    months = [
        'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ]

    parkings = Parking.query.order_by(Parking.address).all()

    query = ParkingSpot.query.options(
        joinedload(ParkingSpot.bookings).joinedload(Booking.client),
        joinedload(ParkingSpot.parking)
    )

    if selected_parking_id:
        query = query.filter_by(parking_id=selected_parking_id)

    spots = query.order_by(ParkingSpot.number).all()

    # === 1) Загружаем суммы оплат по каждому бронированию ===
    payments = (
        db.session.query(Payment.booking_id, db.func.sum(Payment.amount))
        .group_by(Payment.booking_id)
        .all()
    )
    payments_dict = {b_id: total or 0 for b_id, total in payments}

    # === 2) Проставляем sum_paid каждому booking ===
    for spot in spots:
        for b in spot.bookings:
            b.sum_paid = payments_dict.get(b.booking_id, 0)
        spot.bookings_by_month = {}

        for month_index in range(1, 13):
            month_start = date(target_year, month_index, 1)
            month_end = (
                date(target_year + 1, 1, 1) - timedelta(days=1)
                if month_index == 12 else
                date(target_year, month_index + 1, 1) - timedelta(days=1)
            )

            active_booking = None
            for b in spot.bookings:
                if b.start_date <= month_end and b.end_date >= month_start:
                    active_booking = b
                    break

            # === 4) Устанавливаем статус ===
            if active_booking:
                if active_booking.sum_paid >= (active_booking.rent_size or 0):
                    active_booking.status = "занято"
                else:
                    active_booking.status = "забронировано"

            # обновляем статус парковочного места (только для отображения)
            if active_booking:
                spot.status = active_booking.status
            else:
                spot.status = "свободно"

            # ВАЖНО — ДОЛЖНО БЫТЬ ВНУТРИ ЦИКЛА
            spot.bookings_by_month[month_index] = active_booking

    return render_template(
        'workspace.html',
        parkings=parkings,
        spots=spots,
        selected_parking_id=selected_parking_id,
        year_offset=year_offset,
        current_year=target_year,
        months=months,
        datetime=datetime,
        timedelta=timedelta,
        date=date
    )

# ================================================================
@bp.route('/client/<int:client_id>', methods=['GET', 'POST'])
@login_required
def client_card(client_id):
    client = Client.query.get(client_id) if client_id != 0 else None

    # ====== 1. Загружаем текущее бронирование клиента ======
    booking = None
    payment = None

    if client:
        booking = Booking.query.filter_by(client_id=client.client_id).order_by(Booking.start_date.desc()).first()

        if booking:
            payment = Payment.query.filter_by(booking_id=booking.booking_id).order_by(Payment.payment_date.desc()).first()

    # ====== POST: сохранение ======
    if request.method == 'POST':
        spot_id = request.form.get('spot_id', type=int)
        start_raw = request.form.get('start_date')
        end_raw = request.form.get('end_date')
        rent = request.form.get('rent_size', type=float)
        payment_date_raw = request.form.get('payment_date')
        payment_amount = request.form.get('payment_amount', type=float)
        notes = request.form.get('notes', '').strip()

        existing_client_id = request.form.get('existing_client_id', type=int)
        phone = request.form.get('phone', '').strip()

        if not (spot_id and start_raw and end_raw and rent is not None):
            flash("Заполните обязательные поля.", "danger")
            return redirect(request.url)

        start_date = datetime.strptime(start_raw, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_raw, '%Y-%m-%d').date()

        if start_date >= end_date:
            flash("Дата начала должна быть раньше окончания.", "danger")
            return redirect(request.url)

        # выбираем арендатора
        if existing_client_id:
            client = Client.query.get(existing_client_id)
        else:
            flash("Нужно выбрать арендатора.", "danger")
            return redirect(request.url)

        # ===== обновление или создание бронирования =====
        if booking:
            booking.spot_id = spot_id
            booking.start_date = start_date
            booking.end_date = end_date
            booking.rent_size = rent
            booking.notes = notes
        else:
            booking = Booking(
                spot_id=spot_id,
                client_id=client.client_id,
                start_date=start_date,
                end_date=end_date,
                rent_size=rent,
                status="занято"
            )
            db.session.add(booking)
            db.session.flush()

        # ====== платеж ======
        if payment_amount:
            if payment:
                payment.amount = payment_amount
                payment.payment_date = (
                    datetime.strptime(payment_date_raw, "%Y-%m-%d").date()
                    if payment_date_raw else payment.payment_date
                )
            else:
                db.session.add(Payment(
                    booking_id=booking.booking_id,
                    amount=payment_amount,
                    payment_date=(
                        datetime.strptime(payment_date_raw, "%Y-%m-%d").date()
                        if payment_date_raw else date.today()
                    )
                ))

        db.session.commit()

        flash("Бронирование сохранено.", "success")
        return redirect(url_for('workspace.view'))

    # ====== GET: формируем prefill ======
    if booking:
        # если бронь существует — заполняем все
        pre_spot_id = booking.spot_id
        pre_start = booking.start_date.isoformat()
        pre_end = booking.end_date.isoformat()
        pre_rent = booking.rent_size
        pre_notes = booking.notes or ""
        pre_payment_amount = payment.amount if payment else ""
        pre_payment_date = (
            payment.payment_date.strftime('%Y-%m-%d')
            if payment and payment.payment_date else ""
        )
        is_edit = True
    else:
        # если нет — заполняем только GET значения
        pre_spot_id = request.args.get('spot_id', type=int)
        pre_start = request.args.get('prefill_start')
        pre_end = request.args.get('prefill_end')
        pre_rent = ""
        pre_notes = ""
        pre_payment_amount = ""
        pre_payment_date = ""
        is_edit = False

    spots_list = ParkingSpot.query.order_by(ParkingSpot.number).all()
    clients_list = Client.query.order_by(Client.name).all()

    return render_template(
        'client_card.html',
        client=client,
        spots_list=spots_list,
        clients_list=clients_list,

        pre_spot_id=pre_spot_id,
        pre_start=pre_start,
        pre_end=pre_end,
        pre_rent=pre_rent,
        pre_notes=pre_notes,
        pre_payment_amount=pre_payment_amount,
        pre_payment_date=pre_payment_date,

        is_edit=is_edit
    )


# ================================================================
#   СПИСОК АРЕНДАТОРОВ
# ================================================================
@bp.route('/clients')
@login_required
def clients():
    q = request.args.get('q', '').strip()
    sort = request.args.get('sort', '')
    flt = request.args.get('filter', '')

    query = Client.query

    # === Поиск ===
    if q:
        query = query.filter(
            (Client.name.ilike(f"%{q}%")) |
            (Client.phone.ilike(f"%{q}%"))
        )

    # === Сортировка ===
    if sort == "desc":
        query = query.order_by(Client.name.desc())
    else:
        query = query.order_by(Client.name.asc())

    clients = query.all()

    # === Фильтр (требует активных броней) ===
    if flt:
        today = date.today()
        if flt == "active":
            clients = [c for c in clients if any(
                b.start_date <= today <= b.end_date for b in c.bookings
            )]
        elif flt == "inactive":
            clients = [c for c in clients if not any(
                b.start_date <= today <= b.end_date for b in c.bookings
            )]

    return render_template('clients.html', clients=clients, date=date)


# ================================================================
#   ДОБАВЛЕНИЕ АРЕНДАТОРА
# ================================================================
@bp.route('/add_client', methods=['GET', 'POST'])
@login_required
def add_client():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        notes = request.form.get('notes', '').strip()

        if not name:
            flash("Укажите ФИО.", "danger")
            return redirect(request.url)

        db.session.add(Client(
            name=name,
            phone=phone or None,
            notes=notes or None
        ))
        db.session.commit()

        flash("Арендатор добавлен.", "success")
        return redirect(url_for('workspace.view'))

    return render_template('add_client.html')

@bp.route('/edit_client/<int:client_id>', methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    client = Client.query.get_or_404(client_id)

    if request.method == 'POST':
        client.name = request.form.get('name', '').strip()
        client.phone = request.form.get('phone', '').strip()
        client.notes = request.form.get('notes', '').strip() or None

        if not client.name:
            flash("ФИО не может быть пустым.", "danger")
            return redirect(request.url)

        db.session.commit()
        flash("Изменения сохранены.", "success")
        return redirect(url_for('workspace.clients'))

    return render_template("edit_client.html", client=client)
# ================================================================
#   УДАЛЕНИЕ АРЕНДАТОРА
# ================================================================
@bp.route('/delete_client/<int:client_id>', methods=['POST'])
@login_required
def delete_client(client_id):
    c = Client.query.get_or_404(client_id)

    if c.bookings:
        flash("Нельзя удалить арендатора — есть бронирования.", "danger")
        return redirect(url_for('workspace.clients'))

    db.session.delete(c)
    db.session.commit()

    flash("Арендатор удалён.", "success")
    return redirect(url_for('workspace.clients'))


# ================================================================
#   ДОБАВЛЕНИЕ ПАРКОВКИ
# ================================================================
@bp.route('/add_parking', methods=['GET', 'POST'])
@login_required
def add_parking():
    if request.method == 'POST':
        address = request.form.get('address', '').strip()

        if not address:
            flash("Заполните адрес.", "danger")
            return redirect(request.url)

        db.session.add(Parking(address=address))
        db.session.commit()

        flash("Парковка добавлена.", "success")
        return redirect(url_for('workspace.view'))

    return render_template('add_parking.html')


# ================================================================
#   ДОБАВЛЕНИЕ МЕСТА
# ================================================================
@bp.route('/add_spot', methods=['GET', 'POST'])
@login_required
def add_spot():
    parkings = Parking.query.order_by(Parking.address).all()

    if request.method == 'POST':
        parking_id = request.form.get('parking_id', type=int)
        number = request.form.get('number', '').strip()

        if not parking_id or not number:
            flash("Заполните поля.", "danger")
            return redirect(request.url)

        exists = ParkingSpot.query.filter_by(parking_id=parking_id, number=number).first()
        if exists:
            flash("Такое место уже существует.", "warning")
            return redirect(request.url)

        db.session.add(ParkingSpot(parking_id=parking_id, number=number))
        db.session.commit()

        flash("Место добавлено.", "success")
        return redirect(url_for('workspace.view'))

    return render_template('add_spot.html', parkings=parkings)