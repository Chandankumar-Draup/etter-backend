from datetime import datetime, timezone
import math
import os


TEAM_NAME = "gateway"
PURPOSE = "App Notification"


def getCurrentEnvironment() -> str:
    """Get the current environment based on database host or environment variables"""
    db_host = os.environ.get('ETTER_DB_HOST', '')
    
    if 'dev-gateway' in db_host or 'qa' in db_host.lower():
        return 'qa'
    elif 'prod' in db_host.lower():
        return 'prod'
    elif 'localhost' in db_host or '127.0.0.1' in db_host or not db_host:
        return 'dev'
    else:
        return 'dev'


def getLoginLink() -> str:
    """Get the login link based on the current environment"""
    environment = getCurrentEnvironment()
    
    if environment == 'prod':
        return 'https://etter.draup.technology/'
    else:
        return 'https://qa-etter.draup.technology/'


def get_minimized_time_ago(updated_at: datetime) -> str:
    """Fixed timezone handling - assume stored timestamps are in local timezone"""
    if not updated_at:
        return ""
    now = datetime.now()

    if updated_at.tzinfo is not None:
        updated_at = updated_at.replace(tzinfo=None)

    diff = now - updated_at
    seconds = max(0, int(diff.total_seconds()))

    if seconds < 60:
        return f"1m ago"
    elif seconds < 3600:
        return f"{seconds // 60}m ago"
    elif seconds < 86400:
        return f"{seconds // 3600}h ago"
    elif seconds < 604800:
        return f"{seconds // 86400}d ago"
    elif seconds < 2629800:
        return f"{seconds // 604800}w ago"
    elif seconds < 31557600:
        return f"{seconds // 2629800}mo ago"
    else:
        return f"{seconds // 31557600}y ago"
