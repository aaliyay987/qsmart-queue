from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager, login_user, logout_user,
    current_user, login_required
)
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, timedelta, datetime
from sqlalchemy import func, or_
from io import BytesIO
import qrcode
import random

from config import Config
from extensions import db, migrate, socketio
from models import Tenant, Service, Staff, Appointment, Queue, Customer
from sockets import init_socket_events

# App setup
app = Flask(__name__)
app.config.from_object(Config)
app.jinja_env.globals['datetime'] = datetime

# Initialize extensions
db.init_app(app)
migrate.init_app(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
socketio.init_app(app, cors_allowed_origins="*")

# Register SocketIO events
init_socket_events()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Tenant,int(user_id))


# ============================================
# PUBLIC PAGES
# ============================================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        subdomain = request.form.get('subdomain', '').strip()
        owner_email = request.form.get('owner_email', '').strip()
        password = request.form.get('password', '')

        # Validation with proper flash messages
        if not name or not subdomain or not owner_email or not password:
            flash("All fields are required!", "danger")
            return redirect(url_for('signup'))

        # Check if subdomain already exists
        existing_subdomain = Tenant.query.filter_by(subdomain=subdomain).first()
        if existing_subdomain:
            flash("This subdomain is already taken. Please choose another.", "danger")
            return redirect(url_for('signup'))

        # Check if email already exists
        existing_email = Tenant.query.filter_by(owner_email=owner_email).first()
        if existing_email:
            flash("This email is already registered. Please login instead.", "danger")
            return redirect(url_for('signup'))

        # Password length validation
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return redirect(url_for('signup'))
        business_type = request.form.get('business_type', '').strip()

        if not business_type:
            flash("Please select a business type!", "danger")
            return redirect(url_for('signup')) 

        try:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            is_first_user = Tenant.query.count() == 0
            new_tenant = Tenant(
                name=name,
                subdomain=subdomain,
                owner_email=owner_email,
                password_hash=hashed_password,
                business_type=business_type, 
                 is_admin=is_first_user,
                approved=True if is_first_user else False
            )

            db.session.add(new_tenant)
            db.session.commit()

            flash(f"Account created successfully! Please wait for admin approval.", "success")
            return redirect(url_for('login'))

        except Exception as e:
            flash(f"Error creating account: {str(e)}", "danger")
            return redirect(url_for('signup'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash("Email and password are required!", "danger")
            return redirect(url_for('login'))

        tenant = Tenant.query.filter_by(owner_email=email).first()

        if tenant and bcrypt.check_password_hash(tenant.password_hash, password):
            if not tenant.approved:
                flash("Your account is pending approval. Please wait.", "warning")
                return redirect(url_for('login'))

            login_user(tenant)
            flash(f"Welcome back, {tenant.name}!", "success")
            if tenant.is_admin:
                return redirect(url_for('admin_panel'))
            else:
                return redirect(url_for('dashboard'))

        flash("Invalid email or password", "danger")

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully", "info")
    return redirect(url_for('home'))


# ============================================
# OWNER DASHBOARD (LOGIN REQUIRED)
# ============================================

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_panel'))
    services = Service.query.filter_by(tenant_id=current_user.id).all()
    staff = Staff.query.filter_by(tenant_id=current_user.id).all()

    # Active queue
    queues = Queue.query.filter_by(
        tenant_id=current_user.id
    ).filter(
        Queue.status.in_(['waiting', 'in_progress'])
    ).order_by(Queue.position).all()

    # Today's completed services for revenue
    today_completed = Queue.query.filter_by(
        tenant_id=current_user.id,
        status='completed'
    ).filter(
        db.func.date(Queue.created_at) == datetime.utcnow().date()
    ).all()

    # Calculate earnings from completed walk-in services
    earnings = sum([q.service.price for q in today_completed if q.service])

    # Total customers
    total_customers = Customer.query.filter_by(tenant_id=current_user.id).count()

    # Weekly stats
    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_tokens = Queue.query.filter_by(
        tenant_id=current_user.id
    ).filter(Queue.created_at >= week_ago).count()

    # Average wait time estimate
    avg_wait_time = 15 if queues else 0

    return render_template(
        'dashboard.html',
        services=services,
        staff=staff,
        queues=queues,
        earnings=earnings,
        total_customers=total_customers,
        weekly_tokens=weekly_tokens,
        avg_wait_time=avg_wait_time
    )


@app.route('/add_service', methods=['POST'])
@login_required
def add_service():
    try:
        name = request.form.get('name', '').strip()
        duration = request.form.get('duration', '').strip()
        price = request.form.get('price', '').strip()

        if not name or not duration or not price:
            flash("All fields are required!", "danger")
            return redirect(url_for('services_list'))

        duration_int = int(duration)
        price_float = float(price)

        if duration_int <= 0:
            flash("Duration must be greater than 0!", "danger")
            return redirect(url_for('services_list'))
        if price_float < 0:
            flash("Price cannot be negative!", "danger")
            return redirect(url_for('services_list'))

        service = Service(
            name=name,
            duration=duration_int,
            price=price_float,
            tenant_id=current_user.id
        )
        db.session.add(service)
        db.session.commit()
        flash(f"Service '{service.name}' added successfully!", "success")
        
    except ValueError:
        flash("Please enter valid numbers!", "danger")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for('services_list'))


@app.route('/add_staff', methods=['POST'])
@login_required
def add_staff():
    try:
        name = request.form.get('name', '').strip()
        schedule = request.form.get('schedule', '').strip()

        if not name:
            flash("Staff name is required!", "danger")
            return redirect(url_for('staff_list'))

        staff = Staff(
            name=name,
            schedule=schedule,
            tenant_id=current_user.id
        )
        
        db.session.add(staff)
        db.session.commit()
        
        flash(f"Staff member '{staff.name}' added successfully!", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding staff: {str(e)}", "danger")

    return redirect(url_for('staff_list'))


@app.route('/start_service/<int:id>')
@login_required
def start_service(id):
    queue = Queue.query.get_or_404(id)
    if queue.tenant_id == current_user.id:
        queue.status = "in_progress"
        db.session.commit()
        socketio.emit('queue_update', {'queue_id': id, 'status': 'in_progress'})
        flash(f"Started service for token {queue.token}", "info")
    return redirect(url_for('live_queue'))


@app.route('/complete_service/<int:id>')
@login_required
def complete_service(id):
    queue = Queue.query.get_or_404(id)
    if queue.tenant_id == current_user.id:
        queue.status = "completed"
        queue.completed_at = datetime.utcnow()
        
        customer = Customer.query.get(queue.customer_id)
        if customer:
            customer.visits += 1

        db.session.commit()

        # Recalculate all waiting queue positions
        waiting_queues = Queue.query.filter_by(
            tenant_id=current_user.id,
            status='waiting'
        ).order_by(Queue.position).all()

        for idx, q in enumerate(waiting_queues, start=1):
            q.position = idx
            q.estimated_wait = idx * 15

        db.session.commit()

        socketio.emit('queue_update', {'queue_id': id, 'status': 'completed'})
        flash(f"Service completed for token {queue.token}", "success")
        
    return redirect(url_for('live_queue'))


@app.route('/cancel_queue_admin/<int:id>')
@login_required
def cancel_queue_admin(id):
    """Admin cancels a queue entry"""
    queue = Queue.query.get_or_404(id)
    
    if queue.tenant_id != current_user.id:
        flash("Unauthorized action", "danger")
        return redirect(url_for('dashboard'))

    if queue.status in ["waiting", "in_progress"]:
        queue.status = "cancelled"
        db.session.commit()

        # Recalculate positions
        waiting_queues = Queue.query.filter_by(
            tenant_id=current_user.id,
            status='waiting'
        ).order_by(Queue.position).all()

        for idx, q in enumerate(waiting_queues, start=1):
            q.position = idx
            q.estimated_wait = idx * 15

        db.session.commit()

        socketio.emit('queue_update', {'queue_id': id, 'status': 'cancelled'})
        flash(f"Token {queue.token} cancelled.", "info")
    else:
        flash("Cannot cancel this token.", "danger")

    return redirect(url_for('live_queue'))


@app.route('/dashboard/generate_qr')
@login_required
def generate_qr():
    walkin_url = url_for('walkin', subdomain=current_user.subdomain, _external=True)

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(walkin_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)

    return send_file(
        img_io, 
        mimetype='image/png', 
        as_attachment=True, 
        download_name=f'{current_user.subdomain}-qr-code.png'
    )


# ============================================
# CUSTOMER PAGES (NO LOGIN REQUIRED)
# Customers book through search business function
# ============================================

@app.route('/search', methods=['GET', 'POST'])
def search_business():
    """Search for businesses to book appointments"""
    query = request.args.get('q', '').strip()
    results = []

    if query:
        # Search by business name or subdomain
        results = Tenant.query.filter(
            Tenant.approved == True,
            or_(
                Tenant.name.ilike(f'%{query}%'),
                Tenant.subdomain.ilike(f'%{query}%')
            )
        ).all()
    else:
        # Show all approved businesses if no search query
        results = Tenant.query.filter_by(approved=True).all()

    return render_template('search.html', results=results, query=query)


@app.route('/book/<subdomain>', methods=['GET', 'POST'])
def book(subdomain):
    """Customers book appointments here (not owners)"""
    tenant = Tenant.query.filter_by(subdomain=subdomain).first_or_404()
    services = Service.query.filter_by(tenant_id=tenant.id).all()
    staff_list = Staff.query.filter_by(tenant_id=tenant.id).all()

    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            service_id = request.form.get('service_id')
            staff_id = request.form.get('staff_id')
            appointment_time = request.form.get('time')

            if not name or not phone or not service_id or not appointment_time:
                flash("All required fields must be filled!", "danger")
                return redirect(url_for('book', subdomain=subdomain))

            # Check/create customer
            customer = Customer.query.filter_by(
                phone=phone, 
                tenant_id=tenant.id
            ).first()

            if not customer:
                customer = Customer(
                    name=name,
                    phone=phone,
                    tenant_id=tenant.id
                )
                db.session.add(customer)
                db.session.commit()

            # Create appointment (not queue)
            appointment = Appointment(
                customer_id=customer.id,
                service_id=service_id,
                staff_id=staff_id if staff_id else None,
                customer_phone=phone,
                tenant_id=tenant.id,
                time=datetime.fromisoformat(appointment_time),
                status='pending'
            )
            db.session.add(appointment)
            db.session.commit()

            flash(f"Appointment booked successfully for {appointment.time.strftime('%d %b, %I:%M %p')}!", "success")
            return redirect(url_for('search_business'))

        except Exception as e:
            flash(f"Error: {str(e)}", "danger")

    return render_template('book.html', tenant=tenant, services=services, staff_list=staff_list)


@app.route('/walkin/<subdomain>', methods=['GET', 'POST'])
def walkin(subdomain):
    """Customers join walk-in queue here"""
    tenant = Tenant.query.filter_by(subdomain=subdomain).first_or_404()
    services = Service.query.filter_by(tenant_id=tenant.id).all()

    if request.method == 'POST':
        try:
            name = request.form.get('name', 'Walk-in Customer').strip()
            phone = request.form.get('phone', '').strip()
            service_id = request.form.get('service_id')

            if not phone:
                flash("Phone number is required!", "danger")
                return redirect(url_for('walkin', subdomain=subdomain))

            # Check/create customer
            customer = Customer.query.filter_by(
                phone=phone, 
                tenant_id=tenant.id
            ).first()

            if not customer:
                customer = Customer(
                    name=name,
                    phone=phone,
                    tenant_id=tenant.id
                )
                db.session.add(customer)
                db.session.commit()

            # Generate token
            token = f"{tenant.name[:3].upper()}{random.randint(100, 999)}"

            current_queues = Queue.query.filter_by(
                tenant_id=tenant.id,
                status='waiting'
            ).count()

            queue = Queue(
                customer_id=customer.id,
                customer_phone=phone,
                service_id=service_id,
                tenant_id=tenant.id,
                token=token,
                position=current_queues + 1,
                estimated_wait=(current_queues + 1) * 15,
                status="waiting"
            )
            db.session.add(queue)
            db.session.commit()

            flash(f"Your token: {token}. Position: {queue.position}", "success")
            return redirect(url_for('track_queue', id=queue.id))

        except Exception as e:
            flash(f"Error: {str(e)}", "danger")

    return render_template('walkin.html', tenant=tenant, services=services)


@app.route('/quick_add_token', methods=['POST'])
@login_required
def quick_add_token():
    """Quick add token from dashboard (owner only)"""
    try:
        name = request.form.get('name', 'Walk-in Customer').strip()
        phone = request.form.get('phone', '').strip()
        service_id = request.form.get('service_id')

        if not phone:
            flash("Phone number is required!", "danger")
            return redirect(url_for('dashboard'))

        # Check/create customer
        customer = Customer.query.filter_by(
            phone=phone, 
            tenant_id=current_user.id
        ).first()

        if not customer:
            customer = Customer(
                name=name,
                phone=phone,
                tenant_id=current_user.id
            )
            db.session.add(customer)
            db.session.commit()

        # Generate token
        token = f"{current_user.name[:3].upper()}{random.randint(100, 999)}"

        current_queues = Queue.query.filter_by(
            tenant_id=current_user.id,
            status='waiting'
        ).count()

        queue = Queue(
            customer_id=customer.id,
            customer_phone=phone,
            service_id=service_id if service_id else None,
            tenant_id=current_user.id,
            token=token,
            position=current_queues + 1,
            estimated_wait=(current_queues + 1) * 15,
            status="waiting"
        )
        db.session.add(queue)
        
        # Update customer visits
        customer.visits += 1
        
        db.session.commit()

        flash(f"Token {token} added successfully! Position: {queue.position}", "success")
        return redirect(url_for('dashboard'))

    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('dashboard'))


@app.route('/track/<int:id>')
def track_queue(id):
    """Track queue with real-time position updates"""
    queue = Queue.query.get_or_404(id)
    tenant = Tenant.query.get(queue.tenant_id)

    # Real-time position calculation
    if queue.status == 'waiting':
        ahead_count = Queue.query.filter_by(
            tenant_id=queue.tenant_id,
            status='waiting'
        ).filter(Queue.position < queue.position).count()
        
        current_position = ahead_count + 1
        estimated_wait = current_position * 15
    else:
        current_position = queue.position
        estimated_wait = queue.estimated_wait

    return render_template(
        'track.html', 
        queue=queue, 
        tenant=tenant,
        current_position=current_position,
        estimated_wait=estimated_wait
    )


@app.route('/api/queue/<int:id>')
def api_queue_status(id):
    """API endpoint for real-time queue updates"""
    queue = Queue.query.get_or_404(id)

    if queue.status == 'waiting':
        ahead_count = Queue.query.filter_by(
            tenant_id=queue.tenant_id,
            status='waiting'
        ).filter(Queue.position < queue.position).count()
        current_position = ahead_count + 1
        estimated_wait = current_position * 15
    else:
        current_position = queue.position
        estimated_wait = queue.estimated_wait

    return jsonify({
        'token': queue.token,
        'status': queue.status,
        'position': current_position,
        'estimated_wait': estimated_wait
    })


@app.route('/cancel/<int:id>')
def cancel_queue(id):
    """Customer cancels their own queue entry"""
    queue = Queue.query.get_or_404(id)

    if queue.status in ["waiting", "in_progress"]:
        queue.status = "cancelled"
        db.session.commit()

        # Recalculate positions
        waiting_queues = Queue.query.filter_by(
            tenant_id=queue.tenant_id,
            status='waiting'
        ).order_by(Queue.position).all()

        for idx, q in enumerate(waiting_queues, start=1):
            q.position = idx
            q.estimated_wait = idx * 15

        db.session.commit()

        flash("Your token has been cancelled.", "info")
    else:
        flash("Cannot cancel this token.", "danger")

    return redirect(url_for('track_queue', id=id))


# ============================================
# APPOINTMENTS PAGE - OWNER VIEWS CUSTOMER APPOINTMENTS
# ============================================

@app.route('/appointments')
@login_required
def appointments():
    """Owner views all customer appointments (NOT for making appointments)"""
    status = request.args.get('status')

    query = Appointment.query.filter_by(
        tenant_id=current_user.id
    )

    if status:
        query = query.filter_by(status=status)

    all_appointments = query.order_by(Appointment.time.desc()).all()

    # Count by status
    scheduled_count = Appointment.query.filter_by(
        tenant_id=current_user.id,
        status='scheduled'
    ).count()

    completed_count = Appointment.query.filter_by(
        tenant_id=current_user.id,
        status='completed'
    ).count()

    cancelled_count = Appointment.query.filter_by(
        tenant_id=current_user.id,
        status='cancelled'
    ).count()

    return render_template(
        'appointments.html',
        appointments=all_appointments,
        scheduled_count=scheduled_count,
        completed_count=completed_count,
        cancelled_count=cancelled_count
    )


@app.route('/appointment/complete/<int:id>')
@login_required
def complete_appointment(id):
    """Mark appointment as completed"""
    appointment = Appointment.query.get_or_404(id)
    
    if appointment.tenant_id != current_user.id:
        flash("Unauthorized action", "danger")
        return redirect(url_for('appointments'))
    
    appointment.status = 'completed'
    
    # Update customer visit count
    customer = Customer.query.get(appointment.customer_id)
    if customer:
        customer.visits += 1
    
    db.session.commit()
    flash("Appointment marked as completed!", "success")
    return redirect(url_for('appointments'))


@app.route('/appointment/cancel/<int:id>')
@login_required
def cancel_appointment(id):
    """Cancel appointment"""
    appointment = Appointment.query.get_or_404(id)
    
    if appointment.tenant_id != current_user.id:
        flash("Unauthorized action", "danger")
        return redirect(url_for('appointments'))
    
    appointment.status = 'cancelled'
    db.session.commit()
    flash("Appointment cancelled!", "info")
    return redirect(url_for('appointments'))


# ============================================
# ADMIN PANEL
# ============================================

@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for('dashboard'))

    tenants = Tenant.query.all()

    total_tenants = len(tenants)
    approved_tenants = sum(1 for t in tenants if t.approved)
    pending_tenants = total_tenants - approved_tenants

    return render_template(
        'admin.html',
        tenants=tenants,
        total_tenants=total_tenants,
        approved_tenants=approved_tenants,
        pending_tenants=pending_tenants
    )

@app.route('/admin/activate/<int:tenant_id>')
@login_required
def activate_subscription(tenant_id):
    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for('dashboard'))

    tenant = Tenant.query.get_or_404(tenant_id)

    tenant.subscription_active = True
    tenant.subscription_end = datetime.utcnow() + timedelta(days=30)

    db.session.commit()

    flash(f"Subscription activated for {tenant.name}!", "success")
    return redirect(url_for('admin_panel'))

@app.route('/admin/approve/<int:tenant_id>')
@login_required
def approve_tenant(tenant_id):
    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for('dashboard'))

    tenant = Tenant.query.get_or_404(tenant_id)
    tenant.approved = True
    db.session.commit()
    
    flash(f"{tenant.name} approved!", "success")
    return redirect(url_for('admin_panel'))


@app.route('/admin/delete/<int:tenant_id>')
@login_required
def delete_tenant(tenant_id):
    if not current_user.is_admin:
        flash("Access denied", "danger")
        return redirect(url_for('dashboard'))
    tenant = Tenant.query.get_or_404(tenant_id)
    if tenant.id == current_user.id:
        flash("You cannot delete yourself!", "danger")
        return redirect(url_for('admin_panel'))
    

    

    # Delete all related data
    Service.query.filter_by(tenant_id=tenant_id).delete()
    Staff.query.filter_by(tenant_id=tenant_id).delete()
    Queue.query.filter_by(tenant_id=tenant_id).delete()
    Appointment.query.filter_by(tenant_id=tenant_id).delete()
    Customer.query.filter_by(tenant_id=tenant_id).delete()

    db.session.delete(tenant)
    db.session.commit()

    flash(f"Tenant {tenant.name} deleted!", "success")
    return redirect(url_for('admin_panel'))


# ============================================
# OTHER PAGES
# ============================================

@app.route('/live-queue')
@login_required
def live_queue():
    queues = Queue.query.filter_by(
        tenant_id=current_user.id
    ).filter(
        Queue.status.in_(['waiting', 'in_progress'])
    ).order_by(Queue.position).all()
    
    return render_template('live_queue.html', queues=queues)


@app.route('/services')
@login_required
def services_list():
    services = Service.query.filter_by(
        tenant_id=current_user.id
    ).all()
    return render_template('services.html', services=services)


@app.route('/delete_service/<int:id>')
@login_required
def delete_service(id):
    service = Service.query.get_or_404(id)

    if service.tenant_id != current_user.id:
        flash("Unauthorized action", "danger")
        return redirect(url_for('services_list'))

    db.session.delete(service)
    db.session.commit()

    flash("Service deleted successfully", "success")
    return redirect(url_for('services_list'))


@app.route('/staff')
@login_required
def staff_list():
    staff = Staff.query.filter_by(
        tenant_id=current_user.id
    ).all()
    return render_template('staff.html', staff=staff)


@app.route('/delete_staff/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_staff(id):
    staff = Staff.query.get_or_404(id)

    if staff.tenant_id != current_user.id:
        flash("Unauthorized action", "danger")
        return redirect(url_for('staff_list'))

    db.session.delete(staff)
    db.session.commit()

    flash("Staff deleted successfully", "success")
    return redirect(url_for('staff_list'))


@app.route('/customers')
@login_required
def customers_list():
    customers = Customer.query.filter_by(
        tenant_id=current_user.id
    ).order_by(Customer.name.asc()).all()
    
    return render_template('customers.html', customers=customers)


@app.route('/analytics')
@login_required
def analytics():
    tenant_id = current_user.id

    total_customers = Customer.query.filter_by(tenant_id=tenant_id).count()
    total_tokens = Queue.query.filter_by(tenant_id=tenant_id).count()

    completed_queues = Queue.query.filter_by(
        tenant_id=tenant_id,
        status='completed'
    ).all()

    total_revenue = sum(
        q.service.price for q in completed_queues if q.service
    )

    top_customers = Customer.query.filter_by(
        tenant_id=tenant_id
    ).order_by(Customer.visits.desc()).limit(5).all()

    labels = []
    token_data = []

    for i in range(6, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        labels.append(day.strftime("%d %b"))

        count = Queue.query.filter(
            Queue.tenant_id == tenant_id,
            db.func.date(Queue.created_at) == day
        ).count()

        token_data.append(count)

    services = Service.query.filter_by(tenant_id=tenant_id).all()
    service_labels = []
    service_data = []

    for service in services:
        count = Queue.query.filter_by(
            tenant_id=tenant_id,
            service_id=service.id
        ).count()

        service_labels.append(service.name)
        service_data.append(count)

    return render_template(
        'analytics.html',
        total_customers=total_customers,
        total_tokens=total_tokens,
        total_revenue=total_revenue,
        top_customers=top_customers,
        labels=labels,
        token_data=token_data,
        service_labels=service_labels,
        service_data=service_data
    )


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            current_user.name = request.form.get('name', current_user.name)
            current_user.owner_email = request.form.get('email', current_user.owner_email)
            db.session.commit()
            flash("Profile updated successfully!", "success")

        elif action == 'change_password':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if not bcrypt.check_password_hash(current_user.password_hash, current_password):
                flash("Current password is incorrect!", "danger")
            elif new_password != confirm_password:
                flash("New passwords do not match!", "danger")
            elif len(new_password) < 6:
                flash("Password must be at least 6 characters!", "danger")
            else:
                current_user.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
                db.session.commit()
                flash("Password changed successfully!", "success")

        return redirect(url_for('settings'))

    return render_template('settings.html')


@app.route('/')
def home():
    current_year = datetime.now().year

    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_panel'))
        return redirect(url_for('dashboard'))

    return render_template(
        "landing.html",
        logged_in=False,
        current_year=current_year
    )


@app.route('/demo')
def demo():
    return render_template('demo.html')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    socketio.run(
        app,
        debug=True,
        port=5002,
        allow_unsafe_werkzeug=True
    )