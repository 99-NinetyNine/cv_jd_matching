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


# Periodic task schedule (FAST INTERVALS FOR TESTING)
celery_app.conf.beat_schedule = {
    # Test beat scheduler - runs every 2 minutes
    'test-beat-scheduler': {
        'task': 'core.worker.tasks.test_celery_task',
        'schedule': crontab(minute='*/1'),  # Every 2 minutes
    },
    # Parse pending CVs every 1 minute (FAST FOR TESTING)
    'parse-pending-cvs': {
        'task': 'core.worker.tasks.process_batch_cv_parsing',
        'schedule': crontab(minute='*/1'),  # Every 1 minute
    },
    # Compute embeddings for parsed CVs every 2 minutes (FAST FOR TESTING)
    'compute-cv-embeddings': {
        'task': 'core.worker.tasks.submit_cv_batch_embeddings_task',
        'schedule': crontab(minute='*/1'),  # Every 2 minutes
    },
    # Compute embeddings for jobs every 2 minutes (FAST FOR TESTING)
    'compute-job-embeddings': {
        'task': 'core.worker.tasks.submit_batch_job_embeddings_task',
        'schedule': crontab(minute='*/1'),  # Every 2 minutes
    },
    # Generate matches for new CVs every 3 minutes (FAST FOR TESTING)
    'generate-cv-matches': {
        'task': 'core.worker.tasks.perform_batch_matches',
        'schedule': crontab(minute='*/1'),  # Every 3 minutes
    },
    # check for status of batches
    # this can be optimized based on heurtistics of completion times from
    # 3rd party
    'check-batch-status': {
        'task': 'core.worker.tasks.check_batch_status_task',
        'schedule': crontab(minute='*/1'),  # Every 4 minutes
    },
    
}
