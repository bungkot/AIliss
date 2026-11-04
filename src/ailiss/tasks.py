def build_celery_app() -> object | None:
    try:
        from celery import Celery
    except ImportError:
        return None

    from ailiss.config import get_settings

    settings = get_settings()
    broker_url = settings.celery_broker_url or settings.redis_url
    result_backend = settings.celery_result_backend or settings.redis_url
    app = Celery("ailiss", broker=broker_url, backend=result_backend)
    app.conf.update(
        task_track_started=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_time_limit=settings.celery_task_time_limit_seconds,
        task_soft_time_limit=settings.celery_task_soft_time_limit_seconds,
        task_routes={
            "ailiss.tasks.extract": {"queue": "browser"},
            "ailiss.tasks.agent": {"queue": "model"},
            "ailiss.tasks.export": {"queue": "default"},
            "ailiss.tasks.retention": {"queue": "default"},
        },
    )
    return app


app = build_celery_app()


if app is not None:

    @app.task(name="ailiss.tasks.extract", bind=True, max_retries=3, rate_limit="10/m")
    def extract(_task: object, operation_id: str, payload: dict) -> dict[str, str]:
        # Policy-gated mutations remain outside the queue task boundary.
        return {
            "operation_id": operation_id,
            "status": "succeeded",
            "payload_kind": type(payload).__name__,
        }

    @app.task(name="ailiss.tasks.agent", bind=True, max_retries=2)
    def agent(_task: object, operation_id: str, payload: dict) -> dict[str, str]:
        return {
            "operation_id": operation_id,
            "status": "succeeded",
            "payload_kind": type(payload).__name__,
        }

    @app.task(name="ailiss.tasks.export", bind=True, max_retries=3)
    def export(_task: object, operation_id: str, payload: dict) -> dict[str, str]:
        return {
            "operation_id": operation_id,
            "status": "succeeded",
            "payload_kind": type(payload).__name__,
        }

    @app.task(name="ailiss.tasks.retention", bind=True, max_retries=3)
    def retention(_task: object, operation_id: str, payload: dict) -> dict[str, str]:
        return {
            "operation_id": operation_id,
            "status": "succeeded",
            "payload_kind": type(payload).__name__,
        }
