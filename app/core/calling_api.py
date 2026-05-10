import asyncio
import datetime
import logging
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.state.state_manager import StateManager

logger = logging.getLogger("deepbolt.pinger")

# ── Configuration ───────────────────────────────────────────────────────────
PING_INTERVAL_MINUTES = 8
MAX_CONCURRENT_PINGS = 10
HTTP_TIMEOUT_SECONDS = 15
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 3

# ── Module-level scheduler reference (prevents garbage collection) ──────────
_scheduler: AsyncIOScheduler | None = None


# ── Single URL Ping (with retries) ──────────────────────────────────────────
async def ping_url(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    user_id: str,
    url_id: str,
    url: str,
    state_manager: StateManager,
) -> None:
    """Pings a single URL with retry logic and updates the state."""
    async with semaphore:
        status = "Error"
        last_error = None

        for attempt in range(1, MAX_RETRIES + 2):  # 1 initial + MAX_RETRIES retries
            try:
                response = await client.get(url, timeout=HTTP_TIMEOUT_SECONDS)
                status = str(response.status_code)
                logger.info(
                    "✅ Ping OK  | %s | HTTP %s | user=%s",
                    url, status, user_id[:8],
                )
                break  # success — no retry needed

            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    "⏱️  Timeout  | %s | attempt %d/%d | %s",
                    url, attempt, MAX_RETRIES + 1, exc,
                )
            except httpx.RequestError as exc:
                last_error = exc
                logger.warning(
                    "🔌 ConnErr  | %s | attempt %d/%d | %s",
                    url, attempt, MAX_RETRIES + 1, exc,
                )
            except Exception as exc:
                last_error = exc
                logger.error(
                    "❌ Unexpected error pinging %s | attempt %d/%d | %s",
                    url, attempt, MAX_RETRIES + 1, exc,
                )

            # If we still have retries left, back off before the next attempt
            if attempt <= MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * attempt)

        # If all attempts failed, log the final failure
        if status == "Error" and last_error is not None:
            logger.error(
                "🚫 All %d attempts failed for %s | last_error=%s",
                MAX_RETRIES + 1, url, last_error,
            )

        # Persist result regardless of success/failure
        last_ping = datetime.datetime.now().strftime("%b %d, %H:%M")
        try:
            await state_manager.update_url_status(url_id, status, last_ping)
        except Exception as exc:
            logger.error("DB update failed for url_id=%s | %s", url_id, exc)


# ── Batch Ping (all URLs) ──────────────────────────────────────────────────
async def ping_all_urls(state_manager: StateManager) -> None:
    """Iterates through every tracked URL and pings them concurrently."""
    logger.info("🔄 Ping cycle started")

    try:
        tracking_urls = await state_manager.get_all_tracking_urls()
    except Exception as exc:
        logger.error("❌ Failed to fetch URLs from DB — skipping cycle | %s", exc)
        return  # Skip this cycle; the job stays alive for the next interval

    if not tracking_urls:
        logger.info("📭 No URLs to ping — cycle complete")
        return

    logger.info("📡 Pinging %d URL(s)…", len(tracking_urls))

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_PINGS)

    # Connection pool limits prevent socket exhaustion on free-tier hosts
    limits = httpx.Limits(
        max_connections=MAX_CONCURRENT_PINGS,
        max_keepalive_connections=5,
    )

    async with httpx.AsyncClient(
        limits=limits,
        follow_redirects=True,
    ) as client:
        tasks = [
            ping_url(client, semaphore, user_id, url_id, url, state_manager)
            for user_id, url_id, url in tracking_urls
        ]
        # return_exceptions=True ensures one failure doesn't abort the batch
        await asyncio.gather(*tasks, return_exceptions=True)

    logger.info("✅ Ping cycle complete — %d URL(s) processed", len(tracking_urls))


# ── Scheduler Lifecycle ────────────────────────────────────────────────────
def start_scheduler(state_manager: StateManager) -> None:
    """Starts the APScheduler to ping URLs every PING_INTERVAL_MINUTES minutes.

    The scheduler is stored at module level to prevent garbage collection.
    Uses a unique job ID with replace_existing=True to prevent duplicates.
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.warning("⚠️  Scheduler already running — skipping duplicate start")
        return

    _scheduler = AsyncIOScheduler(
        job_defaults={
            "coalesce": True,           # Merge missed runs into one
            "max_instances": 1,         # Never run overlapping instances
            "misfire_grace_time": 600,  # Allow 10 min late execution after sleep
        },
    )

    _scheduler.add_job(
        ping_all_urls,
        trigger="interval",
        minutes=PING_INTERVAL_MINUTES,
        args=[state_manager],
        id="deepbolt_pinger",           # Unique ID prevents duplicates
        replace_existing=True,
        next_run_time=datetime.datetime.now(),  # Fire immediately on startup
    )

    _scheduler.start()
    logger.info(
        "🚀 Scheduler started — pinging every %d minutes (job_id=deepbolt_pinger)",
        PING_INTERVAL_MINUTES,
    )


def shutdown_scheduler() -> None:
    """Gracefully shuts down the scheduler if it's running."""
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("🛑 Scheduler shut down gracefully")
        _scheduler = None


def get_scheduler_status() -> dict:
    """Returns current scheduler status for the /health endpoint."""
    if _scheduler is None:
        return {"running": False, "jobs": 0}

    jobs = _scheduler.get_jobs()
    next_run = None
    if jobs:
        next_run = str(jobs[0].next_run_time)

    return {
        "running": _scheduler.running,
        "jobs": len(jobs),
        "next_run": next_run,
        "interval_minutes": PING_INTERVAL_MINUTES,
    }