from extensions import db
from flask_login import UserMixin
from datetime import datetime


class Tenant(UserMixin, db.Model):
    __tablename__ = 'tenants'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subdomain = db.Column(db.String(50), unique=True, nullable=False)
    owner_email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    approved = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    business_type = db.Column(db.String(50), default='salon')
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    services = db.relationship('Service', backref='tenant', lazy=True, cascade='all, delete-orphan')
    staff = db.relationship('Staff', backref='tenant', lazy=True, cascade='all, delete-orphan')
    queues = db.relationship('Queue', backref='tenant', lazy=True, cascade='all, delete-orphan')
    appointments = db.relationship('Appointment', backref='tenant', lazy=True, cascade='all, delete-orphan')
    customers = db.relationship('Customer', backref='tenant', lazy=True, cascade='all, delete-orphan')
    subscription_active = db.Column(db.Boolean, default=False)
    subscription_end = db.Column(db.DateTime, nullable=True)


class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # minutes
    price = db.Column(db.Float, nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)

    queues = db.relationship('Queue', backref='service', lazy=True)
    appointments = db.relationship('Appointment', backref='service', lazy=True)


class Staff(db.Model):
    __tablename__ = 'staff'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    schedule = db.Column(db.String(200))
    
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    

    appointments = db.relationship('Appointment', backref='staff', lazy=True)


class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    visits = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    queues = db.relationship('Queue', backref='customer', lazy=True)
    appointments = db.relationship('Appointment', backref='customer', lazy=True)


class Queue(db.Model):
    __tablename__ = 'queues'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(20), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    customer_phone = db.Column(db.String(20))
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    position = db.Column(db.Integer, default=1)
    estimated_wait = db.Column(db.Integer, default=15)  # minutes
    status = db.Column(db.String(20), default='waiting')  # waiting, in_progress, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)


class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=True)
    customer_phone = db.Column(db.String(20))
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20))  # pending, confirmed, completed, cancelled
    notes = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)