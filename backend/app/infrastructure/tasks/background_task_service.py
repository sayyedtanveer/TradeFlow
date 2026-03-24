from __future__ import annotations

from fastapi import BackgroundTasks

from backend.app.infrastructure.logging.logger import get_logger
from backend.app.infrastructure.tasks.task_interface import IBackgroundTask

logger = get_logger(__name__)


class BackgroundTaskService:
    """
    Enqueues IBackgroundTask instances via FastAPI BackgroundTasks.

    Usage in a route handler:
        task_service.enqueue(SendWelcomeEmailTask(...), bg_tasks=background_tasks)

    Swap for Celery/ARQ by overriding enqueue() — task implementations stay unchanged.
    """

    def enqueue(
        self,
        task: IBackgroundTask,
        bg_tasks: BackgroundTasks,
    ) -> None:
        """Schedule task.execute() to run after the response is sent."""
        logger.debug("Enqueuing background task", extra={"task": task.task_name})
        bg_tasks.add_task(self._run, task)

    @staticmethod
    async def _run(task: IBackgroundTask) -> None:
        try:
            await task.execute()
        except Exception as exc:
            logger.error(
                "Background task failed",
                extra={"task": task.task_name, "error": str(exc)},
            )
