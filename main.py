import os
import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Body, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from app.state.state_manager import StateManager
from app.core.calling_api import start_scheduler

load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-jwt-keep-it-safe")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")

state_manager = StateManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the background pinger on startup
    start_scheduler(state_manager)
    yield

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
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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

# Endpoints
@app.post("/api/signup")
async def signup(user_data: UserAuth):
    existing_user = await state_manager.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = pwd_context.hash(user_data.password)
    user = await state_manager.create_user(user_data.username, hashed_password)
    return {"message": "User created successfully", "user_id": user["id"]}

@app.post("/api/login")
async def login(user_data: UserAuth):
    user = await state_manager.get_user_by_username(user_data.username)
    if not user or not pwd_context.verify(user_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user["id"]})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/urls")
async def get_urls(current_user: dict = Depends(get_current_user)):
    return await state_manager.get_urls(current_user["id"])

@app.post("/api/urls")
async def add_url(data: UrlCreate, current_user: dict = Depends(get_current_user)):
    url_doc = await state_manager.add_url(current_user["id"], data.url)
    
    # Trigger an immediate background ping for the new URL
    from app.core.calling_api import ping_url
    import httpx
    async def initial_ping():
        async with httpx.AsyncClient() as client:
            await ping_url(client, current_user["id"], url_doc["id"], url_doc["url"], state_manager)
    
    import asyncio
    asyncio.create_task(initial_ping())
    
    return url_doc

@app.delete("/api/urls/{url_id}")
async def delete_url(url_id: str, current_user: dict = Depends(get_current_user)):
    success = await state_manager.delete_url(current_user["id"], url_id)
    if not success:
        raise HTTPException(status_code=404, detail="URL not found")
    return {"message": "URL deleted successfully"}

# Serve frontend
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")