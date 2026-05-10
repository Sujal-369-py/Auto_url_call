# DeepBolt ⚡

A professional, high-performance URL keeper designed to keep your web services (Render, Vercel, etc.) awake and active through periodic automated pings. Features a state-of-the-art **Neutral Obsidian** design system.

![Architecture](https://img.shields.io/badge/Architecture-Asynchronous-00d2ff?style=for-the-badge&logo=fastapi)
![Database](https://img.shields.io/badge/Database-MongoDB-47A248?style=for-the-badge&logo=mongodb)
![Design](https://img.shields.io/badge/Design-Neutral_Obsidian-000000?style=for-the-badge&logo=target)

## ✨ Features

- **Pro-Tier UI/UX**: Sophisticated monochrome design with absolute black backgrounds and high-fidelity micro-animations.
- **Smart Background Pinger**: Automated polling every **8 minutes** using `APScheduler` with retry logic and structured logging.
- **Instant Activation**: New URLs are pinged immediately upon addition for instant status confirmation.
- **Secure Authentication**: Complete JWT-based user system with secure password hashing.
- **Service Isolation**: Multi-user support with strict data isolation via MongoDB.
- **Real-Time Toasts**: Professional feedback system for dashboard interactions.
- **Health Endpoint**: `GET /health` returns scheduler status — ideal for uptime monitors and Render health checks.
- **Production Hardened**: Retry with backoff, concurrency limiting, graceful shutdown, duplicate job protection, and comprehensive logging.

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python 3.10+)
- **Database**: MongoDB (via Motor async driver)
- **Task Scheduling**: APScheduler
- **Frontend**: Vanilla JS, CSS3 (Bespoke Design System), HTML5
- **Networking**: HTTPX (Asynchronous HTTP Client)

## 🚀 Setup Instructions

### 1. Prerequisites
- Python 3.10+ (Specified in `runtime.txt` for Render)
- MongoDB instance (Atlas or local)

### 2. Environment Configuration
Create a `.env` file in the root directory:
```env
DB_URL=mongodb+srv://your_connection_string
SECRET_KEY=your_secure_jwt_secret
```

### 3. Installation
```powershell
pip install -r requirements.txt
```

### 4. Run the Application
```powershell
python -m uvicorn main:app --reload
```
Access the dashboard at `http://localhost:8000`.

## 📂 Project Structure
```text
DeepBolt/
├── app/
│   ├── core/
│   │   └── calling_api.py   # Background pinger with scheduler, retries & logging
│   ├── state/
│   │   └── state_manager.py # MongoDB interaction layer
│   └── static/              # Professional Frontend assets
│       ├── favicon.svg
│       ├── index.html
│       ├── script.js
│       └── style.css
├── main.py                  # FastAPI server, endpoints & health check
├── requirements.txt         # Project dependencies
└── README.md                # Project documentation
```

## 🔧 Production Deployment (Render)

1. Set environment variables `DB_URL` and `SECRET_KEY` in the Render dashboard.
2. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. The `/health` endpoint can be used as Render's health check URL.
4. Scheduler fires every 8 minutes with `misfire_grace_time=600s` to survive Render's free-tier sleep/wake cycles.

## 📜 License
MIT License. Created for professional service monitoring.
