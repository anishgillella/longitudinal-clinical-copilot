"""
Analytics Module

Provides services for analytics, dashboards, and reporting.
"""

from src.analytics.metrics import MetricsService
from src.analytics.dashboard import DashboardService
from src.analytics.reports import ReportService
from src.analytics.progress import ProgressService

__all__ = [
    "MetricsService",
    "DashboardService",
    "ReportService",
    "ProgressService",
]
