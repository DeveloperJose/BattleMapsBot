import time
from collections import deque
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BotStats:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BotStats, cls).__new__(cls)
            cls._instance._init_stats()
        return cls._instance

    def _init_stats(self):
        self.start_time = time.time()

        # API Stats
        self.api_total_count = 0
        self.api_total_duration = 0.0
        self.api_longest_duration = 0.0
        self.api_timestamps = deque()  # Store timestamps for time-window counts

        # Render Stats
        self.render_count = 0
        self.render_total_time = 0.0
        self.render_longest_time = 0.0
        self.render_longest_map_id = 0

    def record_api_request(self, duration: float):
        now = time.time()
        self.api_total_count += 1
        self.api_total_duration += duration
        if duration > self.api_longest_duration:
            self.api_longest_duration = duration
        self.api_timestamps.append(now)
        self._prune_timestamps()

    def record_render(self, duration: float, map_id: int):
        self.render_count += 1
        self.render_total_time += duration
        if duration > self.render_longest_time:
            self.render_longest_time = duration
            self.render_longest_map_id = map_id

    def _prune_timestamps(self):
        # Remove timestamps older than 24 hours
        cutoff = time.time() - 86400
        while self.api_timestamps and self.api_timestamps[0] < cutoff:
            self.api_timestamps.popleft()

    def get_api_stats(self) -> Dict[str, Any]:
        self._prune_timestamps()
        now = time.time()
        one_min = now - 60
        one_hour = now - 3600

        count_24h = len(self.api_timestamps)
        count_1h = 0
        count_1m = 0

        # Iterate backwards since it's sorted
        for ts in reversed(self.api_timestamps):
            if ts > one_min:
                count_1m += 1
            if ts > one_hour:
                count_1h += 1
            else:
                break

        avg_time = (
            self.api_total_duration / self.api_total_count
            if self.api_total_count > 0
            else 0
        )

        return {
            "longest": self.api_longest_duration,
            "average": avg_time,
            "total_uptime": self.api_total_count,
            "total_1m": count_1m,
            "total_1h": count_1h,
            "total_24h": count_24h,
        }

    def get_render_stats(self) -> Dict[str, Any]:
        avg = self.render_total_time / self.render_count if self.render_count > 0 else 0
        return {
            "total_time": self.render_total_time,
            "longest": self.render_longest_time,
            "average": avg,
            "count": self.render_count,
            "longest_map_id": self.render_longest_map_id,
        }
