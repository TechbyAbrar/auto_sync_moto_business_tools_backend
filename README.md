# 🚀 Auto Sync Moto Business – Backend API

Scalable **Django REST API backend** for the Auto Sync Moto Business mobile application, focused on real-time communication, business operations, and modular API delivery.

🔗 **GitHub Repository**: https://github.com/TechbyAbrar/auto_sync_moto_business_tools_backend.git
🎨 **Figma Design**: https://www.figma.com/design/h4u9qpNA05LTQSucM4htPH/j4corp-%7C%7C-AutoSync
🌐 **Live Link**: *(Add when deployed)*

---

## 📌 Overview

Auto Sync Moto Business Backend is designed to support a **mobile-first business automation platform** with:

* real-time communication (chat system)
* business unit & operational management
* scalable API infrastructure
* async-ready backend architecture

The system is built to scale with:

* real-time features (WebSockets)
* multi-module business logic
* high-performance API delivery

---

## 🧠 Core Features

* 🔐 JWT Authentication (SimpleJWT)
* 👤 Custom User Model (`account.UserAuth`)
* 🧾 Business Unit Management
* 💬 Real-time Chat System (Django Channels)
* 📊 Dashboard & Analytics APIs
* 📧 Email Integration (SMTP)
* 🌐 CORS Handling
* 📜 Logging System (rotating logs)
* ⚡ Static file handling (WhiteNoise)

---

## 🏗️ Architecture Overview

Client (Mobile App)
↓
Frontend (Figma-based UI)
↓
Django REST API Backend
↓

| Auth Layer (JWT + Custom User Model) |
| Business Unit Management System      |
| Chat System (WebSocket Layer)        |
| Dashboard & Analytics Engine         |
| Logging & Monitoring                 |

```
    ↓
```

PostgreSQL Database
↓
External Services:

* Redis (Channels Layer)
* SMTP Email Server

---

## ⚙️ Tech Stack

| Category     | Technology            |
| ------------ | --------------------- |
| Language     | Python 3.11+          |
| Framework    | Django 5.2.x          |
| API          | Django REST Framework |
| Realtime     | Django Channels       |
| Broker       | Redis                 |
| Database     | PostgreSQL            |
| Auth         | Simple JWT            |
| Static Files | WhiteNoise            |
| Logging      | Timed Rotating Logs   |

---

## 📁 Project Structure

```text
core/
account/
unit/
privacy/
chatapp/
dashboard/

media/
staticfiles/
logs/

manage.py
requirements.txt
README.md
```

---

## 🔐 Authentication System

* JWT-based authentication
* Bearer token required for protected APIs

### JWT Configuration

* Access Token: 15 days
* Refresh Token: 30 days

```text
Authorization: Bearer <access_token>
```

---

## 💬 Real-time Chat System

* Built with Django Channels
* Redis as message broker
* ASGI-based communication

---

## 📊 Dashboard System

* Business analytics APIs
* Aggregated data endpoints
* Designed for mobile consumption

---

## 📡 API Features

* JWT-secured endpoints
* Modular API design
* Scalable architecture

---

## 🌐 Environment Configuration

Create `.env` file:

```env
SECRET_KEY=your-secret-key
DEBUG=True

DATABASE_URL=postgres://user:password@host:port/dbname

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email
EMAIL_HOST_PASSWORD=your-password
```

---

## 🚀 Installation & Setup

```bash
git clone https://github.com/TechbyAbrar/auto_sync_moto_business_tools_backend.git
cd auto_sync_moto_business_tools_backend

python -m venv env
source env/bin/activate

pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## ⚡ Real-time Setup (Channels)

```bash
redis-server
daphne core.asgi:application
```

---

## 🚀 Production Deployment (ASGI)

### Run with Gunicorn + Uvicorn

```bash
gunicorn core.asgi:application \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

---

## 🧾 Logging System

* Logs stored in `/logs/`
* Daily rotation (5 backups)

Includes:

* API activity logs
* system logs
* error tracking

---

## 🖼️ Screenshots

```md
![App Preview](assets/images/dashboard.png)
```

---

## 🧪 Future Improvements

* Advanced analytics system
* Push notification integration
* Background jobs (Celery + Redis)
* Redis caching layer
* Dockerization
* Microservices transition

---

## 🔐 Security Notes

* Move `SECRET_KEY` to `.env`
* Set `DEBUG=False` in production
* Configure `ALLOWED_HOSTS`
* Restrict CORS origins
* Enable HTTPS

---

## 🤝 Contribution

Pull requests are welcome.

---

## 📄 License

Private / Proprietary

---

## 👨‍💻 Author

**Abraham Qureshi**
Backend Engineer | Django | FastAPI | System Design

🔗 GitHub: https://github.com/TechbyAbrar
