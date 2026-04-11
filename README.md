# DeepBolt ⚡

A professional, high-performance URL keeper designed to keep your web services (Render, Vercel, etc.) awake and active through periodic automated pings. Features a state-of-the-art **Neutral Obsidian** design system.

![Architecture](https://img.shields.io/badge/Architecture-Asynchronous-00d2ff?style=for-the-badge&logo=fastapi)
![Database](https://img.shields.io/badge/Database-MongoDB-47A248?style=for-the-badge&logo=mongodb)
![Design](https://img.shields.io/badge/Design-Neutral_Obsidian-000000?style=for-the-badge&logo=target)

## ✨ Features

- **Pro-Tier UI/UX**: Sophisticated monochrome design with absolute black backgrounds and high-fidelity micro-animations.
- **Smart Background Pinger**: Automated polling every 15 minutes using `APScheduler`.
- **Instant Activation**: New URLs are pinged immediately upon addition for instant status confirmation.
- **Secure Authentication**: Complete JWT-based user system with secure password hashing.
- **Service Isolation**: Multi-user support with strict data isolation via MongoDB.
- **Real-Time Toasts**: Professional feedback system for dashboard interactions.

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python 3.10+)
- **Database**: MongoDB (via Motor async driver)
- **Task Scheduling**: APScheduler
- **Frontend**: Vanilla JS, CSS3 (Bespoke Design System), HTML5
- **Networking**: HTTPX (Asynchronous HTTP Client)

## 🚀 Setup Instructions

### 1. Prerequisites
- Python 3.10+
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
│   │   └── calling_api.py   # Background pinger logic
│   ├── state/
│   │   └── state_manager.py # MongoDB interaction layer
│   └── static/              # Professional Frontend assets
│       ├── favicon.svg
│       ├── index.html
│       ├── script.js
│       └── style.css
├── main.py                  # FastAPI server and endpoints
├── requirements.txt         # Project dependencies
└── README.md                # Project documentation
```

## 📜 License
MIT License. Created for professional service monitoring.
