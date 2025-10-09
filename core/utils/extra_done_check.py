from core.database import db


def is_extra_done(user_id: str, thread_id: str):
    thread = db.users.find_one(
        {"userId": user_id, f"threads.{thread_id}": {"$exists": True}},
        {f"threads.{thread_id}": 1},
    )
    if not thread:
        return False
    return thread.get("threads", {}).get(thread_id, {}).get("extra_done", False)


def mark_extra_done(user_id: str, thread_id: str, value: bool = True):
    try:
        result = db.users.update_one(
            {"userId": user_id, f"threads.{thread_id}": {"$exists": True}},
            {"$set": {f"threads.{thread_id}.extra_done": value}},
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error marking extra_done: {e}")
        return False
