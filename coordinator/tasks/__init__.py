"""
Background tasks package.
"""

from coordinator.tasks.celery_app import celery_app

__all__ = ["celery_app"]
