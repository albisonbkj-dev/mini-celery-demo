from celery import Celery

celery_app = Celery(
    "mini_demo",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
    include=["app.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,
)