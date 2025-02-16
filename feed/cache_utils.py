# cache_utils.py
import json
import os
from datetime import datetime
from django.conf import settings
from pathlib import Path


class VideoCache:
    def __init__(self):
        # Create cache directory if it doesn't exist
        self.cache_dir = Path(settings.BASE_DIR) / "video_cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "youtube_videos.json"

    def get_cached_videos(self):
        try:
            if self.cache_file.exists():
                with open(self.cache_file, "r") as f:
                    data = json.load(f)
                    return data.get("videos", [])
            return None
        except Exception as e:
            return None

    def update_cache(self, videos):
        data = {"last_updated": datetime.now().isoformat(), "videos": videos}
        with open(self.cache_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_last_updated(self):
        try:
            if self.cache_file.exists():
                with open(self.cache_file, "r") as f:
                    data = json.load(f)
                    return data.get("last_updated")
            return None
        except Exception:
            return None


