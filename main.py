import os
import datetime
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Body, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from app.state.state_manager import StateManager
from app.core.calling_api import start_scheduler, shutdown_scheduler, get_scheduler_status, ping_url

load_dotenv()

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("deepbolt.main")

# ── Configuration ───────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-jwt-keep-it-safe")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

# Security
# No longer using passlib due to 3.14 compatibility issues
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

state_manager = StateManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the background pinger on startup
    logger.info("Application starting up…")
    start_scheduler(state_manager)
    yield
    # Graceful shutdown
    logger.info("Application shutting down…")
    shutdown_scheduler()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class UserAuth(BaseModel):
    username: str
    password: str

class UrlCreate(BaseModel):
    url: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Helpers
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await state_manager.get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user

# ── Health Endpoint ─────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """Health check endpoint for Render / monitoring services."""
    return {
        "status": "ok",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scheduler": get_scheduler_status(),
    }

# ── Auth Endpoints ──────────────────────────────────────────────────────────
@app.post("/api/signup")
async def signup(user_data: UserAuth):
    existing_user = await state_manager.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    password_bytes = user_data.password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    user = await state_manager.create_user(user_data.username, hashed_password)
    return {"message": "User created successfully", "user_id": user["id"]}

@app.post("/api/login")
async def login(user_data: UserAuth):
    user = await state_manager.get_user_by_username(user_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    password_bytes = user_data.password.encode('utf-8')
    hashed_bytes = user["password"].encode('utf-8')
    
    if not bcrypt.checkpw(password_bytes, hashed_bytes):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user["id"]})
    return {"access_token": access_token, "token_type": "bearer"}

# ── URL Endpoints ───────────────────────────────────────────────────────────
@app.get("/api/urls")
async def get_urls(current_user: dict = Depends(get_current_user)):
    return await state_manager.get_urls(current_user["id"])

@app.post("/api/urls")
async def add_url(data: UrlCreate, current_user: dict = Depends(get_current_user)):
    url_doc = await state_manager.add_url(current_user["id"], data.url)
    
    # Trigger an immediate background ping for the new URL
    import asyncio
    import httpx

    async def initial_ping():
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                semaphore = asyncio.Semaphore(1)
                await ping_url(client, semaphore, current_user["id"], url_doc["id"], url_doc["url"], state_manager)
        except Exception as exc:
            logger.error("Initial ping failed for %s | %s", url_doc["url"], exc)

    task = asyncio.create_task(initial_ping())

    # Attach a callback so exceptions are logged instead of silently lost
    def _on_done(t: asyncio.Task):
        if t.cancelled():
            logger.warning("Initial ping task was cancelled for %s", url_doc["url"])
        elif t.exception():
            logger.error("Initial ping task exception for %s | %s", url_doc["url"], t.exception())

    task.add_done_callback(_on_done)
    
    return url_doc

@app.delete("/api/urls/{url_id}")
async def delete_url(url_id: str, current_user: dict = Depends(get_current_user)):
    success = await state_manager.delete_url(current_user["id"], url_id)
    if not success:
        raise HTTPException(status_code=404, detail="URL not found")
    return {"message": "URL deleted successfully"}

# Serve frontend
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")