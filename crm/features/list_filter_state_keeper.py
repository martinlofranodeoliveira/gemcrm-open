"""Filter-preserving list state core."""

ALLOWED_VIEWS = ("contacts", "tasks")
KNOWN_TASK_STATUSES = ("open", "overdue", "today", "upcoming", "completed", "all")


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if "view" not in payload:
        raise ValueError("view is required")
    view = payload["view"]
    if not isinstance(view, str):
        raise ValueError("view must be a str")
    if view != "contacts" and view != "tasks":
        raise ValueError("view must be one of contacts, tasks")
    if "q" in payload:
        raw_q = payload["q"]
    else:
        raw_q = ""
    if raw_q is None:
        raw_q = ""
    if not isinstance(raw_q, str):
        raise ValueError("q must be a str")
    q = raw_q.strip()[:200]
    if view == "contacts":
        status = None
        preserved = {}
        if q != "":
            preserved["q"] = q
        total_preserved = len(preserved)
        return {"view": view, "q": q, "status": status, "preserved": preserved, "total_preserved": total_preserved}
    if "status" in payload:
        raw_status = payload["status"]
    else:
        raw_status = None
    if raw_status is None:
        status = "all"
    elif not isinstance(raw_status, str):
        raise ValueError("status must be a str")
    elif raw_status == "":
        status = "all"
    elif raw_status == "open":
        status = "open"
    elif raw_status == "overdue":
        status = "overdue"
    elif raw_status == "today":
        status = "today"
    elif raw_status == "upcoming":
        status = "upcoming"
    elif raw_status == "completed":
        status = "completed"
    elif raw_status == "all":
        status = "all"
    else:
        status = "all"
    preserved = {}
    if q != "":
        preserved["q"] = q
    if status != "all":
        preserved["status"] = status
    total_preserved = len(preserved)
    return {"view": view, "q": q, "status": status, "preserved": preserved, "total_preserved": total_preserved}
