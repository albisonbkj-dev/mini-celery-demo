import time
from app.celery_app import celery_app


@celery_app.task
def process_number(n: int) -> dict:
    # Simulate expensive work
    time.sleep(2)
    return {"input": n, "square": n * n}


@celery_app.task
def aggregate_results(results: list[dict]) -> dict:
    print(results)
    total = sum(item["square"] for item in results)
    return {"items": results, "sum_of_squares": total}