"""
Smart scheduler for news fetching based on source characteristics.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from news.models import HealthStatus

logger = logging.getLogger(__name__)


class SourceSchedule:
    """
    Schedule information for a single news source.
    """
    
    def __init__(
        self,
        source_name: str,
        base_interval: timedelta = timedelta(minutes=30),
        priority: float = 1.0,
        min_interval: timedelta = timedelta(minutes=5),
        max_interval: timedelta = timedelta(hours=6),
    ) -> None:
        self.source_name = source_name
        self.base_interval = base_interval
        self.priority = priority
        self.min_interval = min_interval
        self.max_interval = max_interval
        self.last_fetch = None
        self.next_fetch = datetime.now()
        self.success_count = 0
        self.failure_count = 0
        self.avg_latency = 0.0
        self.update_frequency = base_interval
    
    def update_with_health(self, health: HealthStatus) -> None:
        """
        Update schedule based on health status.
        
        Args:
            health: Health status of the source.
        """
        # Update success/failure counts
        if health.healthy:
            self.success_count += 1
            self.failure_count = 0
            if health.latency_ms:
                # Update average latency
                if self.avg_latency == 0:
                    self.avg_latency = health.latency_ms
                else:
                    self.avg_latency = (self.avg_latency * 9 + health.latency_ms) / 10
        else:
            self.failure_count += 1
            self.success_count = 0
        
        # Adjust update frequency based on success/failure rate and latency
        self._adjust_frequency()
    
    def _adjust_frequency(self) -> None:
        """
        Adjust update frequency based on source characteristics.
        """
        # Base adjustment factor
        adjustment = 1.0
        
        # Adjust based on success/failure rate
        if self.failure_count > 3:
            # Too many failures, increase interval
            adjustment *= 1.5
        elif self.success_count > 5:
            # Consistent success, decrease interval
            adjustment *= 0.8
        
        # Adjust based on latency
        if self.avg_latency > 5000:  # High latency (5s+)
            # High latency, increase interval
            adjustment *= 1.2
        elif self.avg_latency < 1000:  # Low latency (<1s)
            # Low latency, decrease interval
            adjustment *= 0.9
        
        # Calculate new interval
        new_interval = self.base_interval * adjustment
        
        # Clamp to min/max limits
        self.update_frequency = max(self.min_interval, min(self.max_interval, new_interval))
        
        logger.debug(
            f"Source {self.source_name}: adjusted frequency to {self.update_frequency} (adjustment: {adjustment:.2f}, "
            f"success: {self.success_count}, failure: {self.failure_count}, latency: {self.avg_latency:.0f}ms)"
        )
    
    def should_fetch(self, now: datetime) -> bool:
        """
        Check if the source should be fetched now.
        
        Args:
            now: Current datetime.
            
        Returns:
            True if the source should be fetched, False otherwise.
        """
        return now >= self.next_fetch
    
    def mark_fetched(self, now: datetime) -> None:
        """
        Mark the source as fetched at the given time.
        
        Args:
            now: Current datetime.
        """
        self.last_fetch = now
        self.next_fetch = now + self.update_frequency
    
    def get_wait_time(self, now: datetime) -> float:
        """
        Get the time to wait until the next fetch.
        
        Args:
            now: Current datetime.
            
        Returns:
            Wait time in seconds.
        """
        if now >= self.next_fetch:
            return 0.0
        return (self.next_fetch - now).total_seconds()


class NewsScheduler:
    """
    Smart scheduler for managing news source fetching.
    """
    
    def __init__(self) -> None:
        self._schedules: Dict[str, SourceSchedule] = {}
    
    def register_source(
        self,
        source_name: str,
        base_interval: timedelta = timedelta(minutes=30),
        priority: float = 1.0,
        min_interval: timedelta = timedelta(minutes=5),
        max_interval: timedelta = timedelta(hours=6),
    ) -> None:
        """
        Register a news source with the scheduler.
        
        Args:
            source_name: Name of the news source.
            base_interval: Base fetch interval.
            priority: Source priority (higher = more important).
            min_interval: Minimum fetch interval.
            max_interval: Maximum fetch interval.
        """
        self._schedules[source_name] = SourceSchedule(
            source_name=source_name,
            base_interval=base_interval,
            priority=priority,
            min_interval=min_interval,
            max_interval=max_interval,
        )
    
    def update_source_health(self, health: HealthStatus) -> None:
        """
        Update a source's health status and adjust its schedule.
        
        Args:
            health: Health status of the source.
        """
        if health.name in self._schedules:
            self._schedules[health.name].update_with_health(health)
    
    def get_sources_to_fetch(self, now: Optional[datetime] = None) -> List[str]:
        """
        Get a list of sources that should be fetched now, sorted by priority.
        
        Args:
            now: Current datetime (defaults to now).
            
        Returns:
            List of source names that should be fetched now, sorted by priority.
        """
        now = now or datetime.now()
        sources_to_fetch = []
        
        for source_name, schedule in self._schedules.items():
            if schedule.should_fetch(now):
                sources_to_fetch.append((source_name, schedule.priority))
        
        # Sort by priority (highest first)
        sources_to_fetch.sort(key=lambda x: x[1], reverse=True)
        
        return [source_name for source_name, _ in sources_to_fetch]
    
    def mark_source_fetched(self, source_name: str, now: Optional[datetime] = None) -> None:
        """
        Mark a source as fetched at the given time.
        
        Args:
            source_name: Name of the news source.
            now: Current datetime (defaults to now).
        """
        now = now or datetime.now()
        if source_name in self._schedules:
            self._schedules[source_name].mark_fetched(now)
    
    def get_source_schedule(self, source_name: str) -> Optional[SourceSchedule]:
        """
        Get the schedule for a specific source.
        
        Args:
            source_name: Name of the news source.
            
        Returns:
            SourceSchedule for the source, or None if not found.
        """
        return self._schedules.get(source_name)
    
    def get_all_schedules(self) -> Dict[str, SourceSchedule]:
        """
        Get all source schedules.
        
        Returns:
            Dict of source names to SourceSchedule objects.
        """
        return self._schedules.copy()
    
    def get_next_fetch_time(self) -> Optional[datetime]:
        """
        Get the next fetch time for any source.
        
        Returns:
            Next fetch time, or None if no sources are registered.
        """
        if not self._schedules:
            return None
        
        return min(schedule.next_fetch for schedule in self._schedules.values())
    
    def get_wait_time_until_next_fetch(self, now: Optional[datetime] = None) -> float:
        """
        Get the wait time until the next fetch for any source.
        
        Args:
            now: Current datetime (defaults to now).
            
        Returns:
            Wait time in seconds, or 0 if no sources are registered.
        """
        now = now or datetime.now()
        next_fetch = self.get_next_fetch_time()
        if next_fetch is None:
            return 0.0
        
        wait_time = (next_fetch - now).total_seconds()
        return max(0.0, wait_time)