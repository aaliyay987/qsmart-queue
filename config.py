# config.py - Configuration for QSmart Flask app

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')  or "dev-secret-key-123"
    
    # Use your REAL Supabase/Neon PostgreSQL URL here!
    # Example from Supabase: postgresql://postgres:[YOUR_PASSWORD]@db.yourprojectref.supabase.co:5432/postgres
    SQLALCHEMY_DATABASE_URI = ('postgresql://neondb_owner:npg_t9mjJIecb1wP@ep-bold-cake-a11nx6cg-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    print("Loaded DB URI from config:", SQLALCHEMY_DATABASE_URI)