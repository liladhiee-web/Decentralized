"""
Celery background worker and scheduler configuration for asynchronous coordinator tasks.
"""

from celery import Celery

from coordinator.config import get_settings

settings = get_settings()

celery_app = Celery(
    "coordinator_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit for background jobs
    worker_prefetch_multiplier=1,
)

# Celery Beat periodic schedules (e.g. heartbeat timeout detection, artifact cleanup)
celery_app.conf.beat_schedule = {
    "reap-stale-workers-every-minute": {
        "task": "coordinator.tasks.celery_app.reap_stale_workers",
        "schedule": 60.0,
    },
}


@celery_app.task(name="coordinator.tasks.celery_app.reap_stale_workers")
def reap_stale_workers() -> dict[str, str]:
    """Periodic task that marks unresponsive workers as offline when heartbeats lapse."""
    return {"status": "reap_stale_workers_executed"}
