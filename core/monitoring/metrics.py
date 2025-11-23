from core.db.models import SystemMetric
from core.db.engine import engine
from sqlmodel import Session
import time
import functools
from datetime import datetime

def log_metric(name: str, value: float, tags: dict = None):
    try:
        with Session(engine) as session:
            metric = SystemMetric(name=name, value=value, tags=tags or {})
            session.add(metric)
            session.commit()
    except Exception as e:
        print(f"Failed to log metric {name}: {e}")

def track_time(name: str, tags: dict = None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start) * 1000 # ms
                log_metric(name, duration, tags)
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000 # ms
                log_metric(name, duration, {**(tags or {}), "error": str(e)})
                raise e
        return wrapper
    return decorator

async def track_time_async(name: str, tags: dict = None):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start) * 1000 # ms
                log_metric(name, duration, tags)
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000 # ms
                log_metric(name, duration, {**(tags or {}), "error": str(e)})
                raise e
        return wrapper
    return decorator
