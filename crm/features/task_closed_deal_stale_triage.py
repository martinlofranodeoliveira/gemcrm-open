MAX_PK = 9007199254740991
MIN_PK = 1
MAX_ITEMS = 100
MAX_TITLE_LEN = 180
VALID_STAGES = ("new", "qualified", "proposal", "won", "lost")
CLOSED_STAGES = ("won", "lost")

def _check_pk(value):
    if type(value) is not int:
        return False
    if value < 1:
        return False
    if value > 9007199254740991:
        return False
    return True

def _check_title(value):
    if type(value) is not str:
        return False
    if len(value) < 1:
        return False
    if len(value) > 180:
        return False
    return True

def _check_completed(value):
    return type(value) is bool

def _check_deal_pk(value):
    if value is None:
        return True
    if type(value) is not int:
        return False
    if value < 1:
        return False
    if value > 9007199254740991:
        return False
    return True

def _check_stage(value):
    if type(value) is not str:
        return False
    if value not in VALID_STAGES:
        return False
    return True

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be dict")
    if "tasks" in payload:
        tasks_in = payload["tasks"]
    else:
        tasks_in = []
    if "deals" in payload:
        deals_in = payload["deals"]
    else:
        deals_in = []
    if tasks_in is None:
        raise ValueError("tasks must be list")
    if deals_in is None:
        raise ValueError("deals must be list")
    if not isinstance(tasks_in, list):
        raise ValueError("tasks must be list")
    if not isinstance(deals_in, list):
        raise ValueError("deals must be list")
    if len(tasks_in) > 100:
        raise ValueError("tasks too long")
    if len(deals_in) > 100:
        raise ValueError("deals too long")
    seen_task = {}
    task_pks = []
    task_completed = {}
    task_deal = {}
    for item in tasks_in:
        if not isinstance(item, dict):
            raise ValueError("task must be dict")
        if "pk" not in item:
            raise ValueError("task pk missing")
        if "title" not in item:
            raise ValueError("task title missing")
        if "completed" not in item:
            raise ValueError("task completed missing")
        if "deal_pk" not in item:
            raise ValueError("task deal_pk missing")
        pk = item["pk"]
        title = item["title"]
        completed = item["completed"]
        deal_pk = item["deal_pk"]
        if not _check_pk(pk):
            raise ValueError("bad task pk")
        if not _check_title(title):
            raise ValueError("bad task title")
        if not _check_completed(completed):
            raise ValueError("bad task completed")
        if not _check_deal_pk(deal_pk):
            raise ValueError("bad task deal_pk")
        if pk in seen_task:
            raise ValueError("duplicate task pk")
        seen_task[pk] = True
        task_pks.append(pk)
        task_completed[pk] = completed
        task_deal[pk] = deal_pk
    seen_deal = {}
    deal_stage = {}
    for item in deals_in:
        if not isinstance(item, dict):
            raise ValueError("deal must be dict")
        if "pk" not in item:
            raise ValueError("deal pk missing")
        if "stage" not in item:
            raise ValueError("deal stage missing")
        pk = item["pk"]
        stage = item["stage"]
        if not _check_pk(pk):
            raise ValueError("bad deal pk")
        if not _check_stage(stage):
            raise ValueError("bad deal stage")
        if pk in seen_deal:
            raise ValueError("duplicate deal pk")
        seen_deal[pk] = True
        deal_stage[pk] = stage
    stale_pks = []
    open_linked_pks = []
    unlinked_pks = []
    unknown_pks = []
    completed_pks = []
    for pk in task_pks:
        completed = task_completed[pk]
        deal_pk = task_deal[pk]
        if completed is True:
            completed_pks.append(pk)
        else:
            if deal_pk is None:
                unlinked_pks.append(pk)
            else:
                if deal_pk not in deal_stage:
                    unknown_pks.append(pk)
                else:
                    stage = deal_stage[deal_pk]
                    if stage in CLOSED_STAGES:
                        stale_pks.append(pk)
                    else:
                        open_linked_pks.append(pk)
    stale_pks = sorted(stale_pks)
    open_linked_pks = sorted(open_linked_pks)
    unlinked_pks = sorted(unlinked_pks)
    unknown_pks = sorted(unknown_pks)
    completed_pks = sorted(completed_pks)
    task_count = len(task_pks)
    completed_count = len(completed_pks)
    stale_count = len(stale_pks)
    open_linked_count = len(open_linked_pks)
    unlinked_count = len(unlinked_pks)
    unknown_count = len(unknown_pks)
    open_count = stale_count + open_linked_count + unlinked_count + unknown_count
    return {"task_count": task_count, "open_count": open_count, "completed_count": completed_count, "stale_count": stale_count, "open_linked_count": open_linked_count, "unlinked_count": unlinked_count, "unknown_count": unknown_count, "stale_pks": stale_pks, "open_linked_pks": open_linked_pks, "unlinked_pks": unlinked_pks, "unknown_pks": unknown_pks, "completed_pks": completed_pks}
