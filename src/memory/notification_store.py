import logging
import uuid
import time
from typing import Dict, List, Optional
from threading import Lock

logger = logging.getLogger("notification_store")

class NotificationStore:
    """
    In-memory store for user notifications.
    Because we run a single uvicorn worker, a class-level dictionary is sufficient
    for holding ephemeral session alerts like "Daily Login Insights".
    """
    _store: Dict[str, List[Dict]] = {}
    _lock = Lock()
    
    @classmethod
    def add_notification(cls, user_email: str, markdown_content: str, title: str = "Market Insight") -> str:
        with cls._lock:
            if user_email not in cls._store:
                cls._store[user_email] = []
                
            notif_id = str(uuid.uuid4())
            notif = {
                "id": notif_id,
                "title": title,
                "content": markdown_content,
                "timestamp": int(time.time() * 1000),
                "read": False
            }
            
            # Keep only the 5 most recent notifications per user
            cls._store[user_email].insert(0, notif)
            cls._store[user_email] = cls._store[user_email][:5]
            
            logger.info("Added notification %s for user %s", notif_id, user_email)
            return notif_id
            
    @classmethod
    def get_unread(cls, user_email: str) -> List[Dict]:
        with cls._lock:
            return [n for n in cls._store.get(user_email, []) if not n["read"]]
            
    @classmethod
    def mark_read(cls, user_email: str, notif_id: str) -> bool:
        with cls._lock:
            for n in cls._store.get(user_email, []):
                if n["id"] == notif_id:
                    n["read"] = True
                    return True
            return False
            
    @classmethod
    def clear_all(cls, user_email: str):
        with cls._lock:
            if user_email in cls._store:
                cls._store[user_email] = []
