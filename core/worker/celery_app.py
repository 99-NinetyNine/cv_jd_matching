from celery import Celery
from celery.schedules import crontab
import os

redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = os.getenv("REDIS_PORT", "6379")
redis_url = f"redis://{redis_host}:{redis_port}/0"

celery_app = Celery(
    "cv_worker",
    broker=redis_url,
    backend=redis_url,
    include=["core.worker.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,  # For long-running tasks
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks (memory management)
)

# Periodic task schedule
celery_app.conf.beat_schedule = {
    # Test beat scheduler - runs every 2 minutes
    'test-beat-scheduler': {
        'task': 'core.worker.tasks.test_beat_task',
        'schedule': crontab(minute='*/2'),  # Every 2 minutes
    },
    # Parse pending CVs every 5 minutes
    # 'parse-pending-cvs': {
    #     'task': 'core.worker.tasks.process_batch_cv_parsing',
    #     'schedule': crontab(minute='*/5'),  # Every 5 minutes
    # },
    # Compute embeddings for parsed CVs every 10 minutes
    # 'compute-cv-embeddings': {
    #     'task': 'core.worker.tasks.compute_pending_cv_embeddings',
    #     'schedule': crontab(minute='*/10'),  # Every 10 minutes
    # },
    # Compute embeddings for jobs every 15 minutes
    # 'compute-job-embeddings': {
    #     'task': 'core.worker.tasks.compute_pending_job_embeddings',
    #     'schedule': crontab(minute='*/15'),  # Every 15 minutes
    # },
    # Generate matches for new CVs every 20 minutes
    # 'generate-cv-matches': {
    #     'task': 'core.worker.tasks.generate_matches_for_new_cvs',
    #     'schedule': crontab(minute='*/20'),  # Every 20 minutes
    # },
    # Generate explanations for matches every 30 minutes
    # 'generate-explanations': {
    #     'task': 'core.worker.tasks.generate_batch_explanations',
    #     'schedule': crontab(minute='*/30'),  # Every 30 minutes
    # },
    # Retry failed embeddings once per hour
    # 'retry-failed-embeddings': {
    #     'task': 'core.worker.tasks.retry_failed_embeddings',
    #     'schedule': crontab(minute=0),  # Every hour
    # },
    # Clean up old data daily at 2 AM
    # 'cleanup-old-data': {
    #     'task': 'core.worker.tasks.cleanup_old_data',
    #     'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    # },
}
