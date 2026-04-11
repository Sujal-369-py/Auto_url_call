import asyncio
import datetime
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.state.state_manager import StateManager

async def ping_url(client: httpx.AsyncClient, user_id: str, url_id: str, url: str, state_manager: StateManager):
    """Pings a single URL and updates the state"""
    try:
        print(f"[{datetime.datetime.now()}] Pinging {url} for user {user_id}...")
        response = await client.get(url, timeout=10.0)
        status = str(response.status_code)
    except Exception as e:
        print(f"Error pinging {url}: {e}")
        status = "Error"
    
    last_ping = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await state_manager.update_url_status(url_id, status, last_ping)

async def ping_all_urls(state_manager: StateManager):
    """Iterates through all URLs and pings them"""
    async with httpx.AsyncClient() as client:
        tracking_urls = await state_manager.get_all_tracking_urls()
        tasks = []
        for user_id, url_id, url in tracking_urls:
            tasks.append(ping_url(client, user_id, url_id, url, state_manager))
        
        if tasks:
            await asyncio.gather(*tasks)

def start_scheduler(state_manager: StateManager):
    """Starts the APScheduler to ping URLs every 15 minutes"""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(ping_all_urls, 'interval', minutes=15, args=[state_manager], next_run_time=datetime.datetime.now())
    scheduler.start()
    print("Background pinger started (every 15 minutes)")