# QSmart — Smart Queue & Appointment Management System

> T.Y.B.Sc. Computer Science — Semester VI Project | A.Y. 2025-2026

A fully functional, multi-tenant web application built with **Python Flask** for managing queues, appointments, and customers at small Indian service businesses (salons, clinics, coaching centres, etc.)

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the App
```bash
python app.py
```

### 3. Open in Browser
```
http://localhost:5002
```

---

## 🔑 Default Admin Account
```
Email:    admin@qsmart.in
Password: admin123
```

---

## 📁 Project Structure

```
qsmart/
├── app.py              # Main Flask application (all routes)
├── config.py           # Configuration settings
├── extensions.py       # Flask extensions (db, socketio, migrate)
├── models.py           # Database models (Tenant, Service, Staff, Queue, Appointment, Customer)
├── sockets.py          # WebSocket event handlers
├── requirements.txt    # Python dependencies
└── templates/
    ├── base.html           # Base layout with sidebar navigation
    ├── landing.html        # Public landing page
    ├── login.html          # Owner login page
    ├── signup.html         # Owner registration page
    ├── dashboard.html      # Main owner dashboard
    ├── live_queue.html     # Live queue management
    ├── appointments.html   # Appointment management
    ├── customers.html      # Customer database
    ├── services.html       # Service management
    ├── staff.html          # Staff management
    ├── analytics.html      # Analytics with Chart.js
    ├── settings.html       # Business settings
    ├── admin.html          # Super-admin panel
    ├── walkin.html         # Customer walk-in page (PUBLIC)
    ├── book.html           # Customer appointment booking (PUBLIC)
    ├── track.html          # Queue tracking page (PUBLIC)
    └── demo.html           # Interactive demo — NO LOGIN REQUIRED
```

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🔐 Multi-Tenant Auth | Each business is completely isolated |
| 🎟️ QR Token System | Walk-in customers scan QR → get digital token |
| 📅 Online Appointments | 24/7 booking via unique link |
| ⚡ Real-Time Queue | WebSocket-powered live updates |
| 📊 Analytics Dashboard | Chart.js charts, revenue tracking |
| 🔔 WhatsApp Alerts | Automated notifications via Ultramsg API |
| 👥 Customer Database | Auto-tracks visits per customer |
| 👨‍💼 Staff Management | Assign staff to appointments |
| 📱 Mobile Responsive | Works on all devices |
| 🎭 Demo Mode | Try QSmart without creating an account |

---

## 🛣️ Key Routes

### Public Pages
| Route | Description |
|---|---|
| `/` | Landing page |
| `/signup` | Register your business |
| `/login` | Business owner login |
| `/demo` | **Interactive demo — no login needed** |
| `/walkin/<subdomain>` | Customer walk-in token page |
| `/book/<subdomain>` | Customer appointment booking |
| `/track/<id>` | Track queue token status |

### Owner Dashboard (Login Required)
| Route | Description |
|---|---|
| `/dashboard` | Main dashboard |
| `/live-queue` | Live queue table |
| `/appointments` | Appointment management |
| `/customers` | Customer list |
| `/services` | Service management |
| `/staff` | Staff management |
| `/analytics` | Charts and reports |
| `/settings` | Business settings |
| `/dashboard/generate_qr` | Download QR code |

### API
| Route | Description |
|---|---|
| `/api/queue/<subdomain>` | JSON queue status |
| `/api/token/<id>/status` | JSON token status |

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.x, Flask 3.0 |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM | Flask-SQLAlchemy + Flask-Migrate |
| Real-Time | Flask-SocketIO (WebSockets) |
| Auth | Flask-Login + Flask-Bcrypt |
| QR Code | qrcode + Pillow |
| Frontend | Bootstrap 5, Chart.js, Vanilla JS |
| Notifications | Ultramsg WhatsApp API |
| Deployment | Render / Railway + Supabase |

---

## 📦 Deployment (Render/Railway)

1. Push to GitHub
2. Connect to Render/Railway
3. Set environment variable: `DATABASE_URL=postgresql://...`
4. Set `SECRET_KEY=your-secret-key`
5. Build command: `pip install -r requirements.txt`
6. Start command: `python app.py`

---

## 👩‍💻 Author
**Aaliya Thakur** | Roll No: 22 | T.Y.B.Sc. Computer Science, Sem VI