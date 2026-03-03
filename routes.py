from flask import render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, current_user
from app import app, db
from models import Tenant
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password'])
        subdomain = name.lower().replace(' ', '')  # Auto-generate
        tenant = Tenant(name=name, subdomain=subdomain, owner_email=email, password_hash=password)
        db.session.add(tenant)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

# Add login route similarly