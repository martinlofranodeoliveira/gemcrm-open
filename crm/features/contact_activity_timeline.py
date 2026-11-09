import re

_MAX_PK = 9007199254740991
_MAX_LEN = 180
_MAX_DEALS = 100
_MAX_TASKS = 200
_STAGES = ("new", "qualified", "proposal", "won", "lost")


def _is_pk(value):
    if type(value) is not int:
        return False
    if value < 1:
        return False
    if value > _MAX_PK:
        return False
    return True


def _is_text(value):
    if type(value) is not str:
        return False
    if len(value) < 1:
        return False
    if len(value) > _MAX_LEN:
        return False
    return True


def _is_stage(value):
    if type(value) is not str:
        return False
    if value in _STAGES:
        return True
    return False


def _is_leap_year(year):
    if year % 4 != 0:
        return False
    if year % 100 != 0:
        return True
    if year % 400 != 0:
        return False
    return True


def _is_due_date(value):
    if type(value) is not str:
        return False
    if len(value) != 10:
        return False
    if re.match("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", value) is None:
        return False
    year = int(value[0:4])
    month = int(value[5:7])
    day = int(value[8:10])
    if month < 1:
        return False
    if month > 12:
        return False
    if day < 1:
        return False
    if month == 2:
        if _is_leap_year(year):
            if day > 29:
                return False
        else:
            if day > 28:
                return False
    else:
        if month == 4 or month == 6 or month == 9 or month == 11:
            if day > 30:
                return False
        else:
            if day > 31:
                return False
    return True


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload")
    if "contact" not in payload:
        raise ValueError("contact")
    contact = payload["contact"]
    if not isinstance(contact, dict):
        raise ValueError("contact")
    if "pk" not in contact:
        raise ValueError("contact.pk")
    if "name" not in contact:
        raise ValueError("contact.name")
    contact_pk = contact["pk"]
    contact_name = contact["name"]
    if not _is_pk(contact_pk):
        raise ValueError("contact.pk")
    if not _is_text(contact_name):
        raise ValueError("contact.name")
    if "deals" not in payload:
        deals = []
    else:
        deals = payload["deals"]
        if deals is None:
            raise ValueError("deals")
        if not isinstance(deals, list):
            raise ValueError("deals")
    if "tasks" not in payload:
        tasks = []
    else:
        tasks = payload["tasks"]
        if tasks is None:
            raise ValueError("tasks")
        if not isinstance(tasks, list):
            raise ValueError("tasks")
    if len(deals) > _MAX_DEALS:
        raise ValueError("deals")
    if len(tasks) > _MAX_TASKS:
        raise ValueError("tasks")
    seen_deals = {}
    for deal in deals:
        if not isinstance(deal, dict):
            raise ValueError("deal")
        if "pk" not in deal:
            raise ValueError("deal.pk")
        if "title" not in deal:
            raise ValueError("deal.title")
        if "stage" not in deal:
            raise ValueError("deal.stage")
        if "contact_pk" not in deal:
            raise ValueError("deal.contact_pk")
        d_pk = deal["pk"]
        d_title = deal["title"]
        d_stage = deal["stage"]
        d_cpk = deal["contact_pk"]
        if not _is_pk(d_pk):
            raise ValueError("deal.pk")
        if not _is_text(d_title):
            raise ValueError("deal.title")
        if not _is_stage(d_stage):
            raise ValueError("deal.stage")
        if d_cpk is None:
            pass
        else:
            if not _is_pk(d_cpk):
                raise ValueError("deal.contact_pk")
        if d_pk in seen_deals:
            raise ValueError("deal.pk")
        seen_deals[d_pk] = True
    seen_tasks = {}
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("task")
        if "pk" not in task:
            raise ValueError("task.pk")
        if "title" not in task:
            raise ValueError("task.title")
        if "due_date" not in task:
            raise ValueError("task.due_date")
        if "completed" not in task:
            raise ValueError("task.completed")
        if "deal_pk" not in task:
            raise ValueError("task.deal_pk")
        t_pk = task["pk"]
        t_title = task["title"]
        t_due = task["due_date"]
        t_comp = task["completed"]
        t_dpk = task["deal_pk"]
        if not _is_pk(t_pk):
            raise ValueError("task.pk")
        if not _is_text(t_title):
            raise ValueError("task.title")
        if not _is_due_date(t_due):
            raise ValueError("task.due_date")
        if type(t_comp) is not bool:
            raise ValueError("task.completed")
        if t_dpk is None:
            pass
        else:
            if not _is_pk(t_dpk):
                raise ValueError("task.deal_pk")
        if t_pk in seen_tasks:
            raise ValueError("task.pk")
        seen_tasks[t_pk] = True
    linked_deals = []
    for deal in deals:
        if deal["contact_pk"] == contact_pk:
            linked_deals.append({"pk": deal["pk"], "title": deal["title"], "stage": deal["stage"]})
    n = len(linked_deals)
    i = 0
    while i < n:
        j = i + 1
        while j < n:
            if linked_deals[j]["pk"] < linked_deals[i]["pk"]:
                tmp = linked_deals[i]
                linked_deals[i] = linked_deals[j]
                linked_deals[j] = tmp
            j = j + 1
        i = i + 1
    linked_ids = {}
    for item in linked_deals:
        linked_ids[item["pk"]] = True
    linked_tasks = []
    for task in tasks:
        t_dpk = task["deal_pk"]
        if t_dpk is None:
            continue
        if t_dpk in linked_ids:
            linked_tasks.append({"pk": task["pk"], "title": task["title"], "due_date": task["due_date"], "completed": task["completed"], "deal_pk": task["deal_pk"]})
    m = len(linked_tasks)
    i = 0
    while i < m:
        j = i + 1
        while j < m:
            a_date = linked_tasks[i]["due_date"]
            b_date = linked_tasks[j]["due_date"]
            a_pk = linked_tasks[i]["pk"]
            b_pk = linked_tasks[j]["pk"]
            swap = False
            if b_date < a_date:
                swap = True
            else:
                if b_date == a_date:
                    if b_pk < a_pk:
                        swap = True
            if swap:
                tmp = linked_tasks[i]
                linked_tasks[i] = linked_tasks[j]
                linked_tasks[j] = tmp
            j = j + 1
        i = i + 1
    deal_count = len(deals)
    task_count = len(tasks)
    linked_deal_count = len(linked_deals)
    linked_task_count = len(linked_tasks)
    return {"contact_pk": contact_pk, "contact_name": contact_name, "deal_count": deal_count, "task_count": task_count, "linked_deal_count": linked_deal_count, "linked_task_count": linked_task_count, "linked_deals": linked_deals, "linked_tasks": linked_tasks}
