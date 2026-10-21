"""Record delete impact preview core. Pure deterministic preview."""

MIN_PK = 1
MAX_PK = 9007199254740991
MAX_ENTRIES = 2000
ALLOWED_KINDS = ("company", "contact", "deal", "task")


def _is_pk(value):
    if type(value) is not int:
        return False
    if value < MIN_PK:
        return False
    if value > MAX_PK:
        return False
    return True


def _is_fk(value):
    if value is None:
        return True
    if type(value) is not int:
        return False
    if value < MIN_PK:
        return False
    if value > MAX_PK:
        return False
    return True


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    if "target" not in payload:
        raise ValueError("target missing")
    target = payload["target"]
    if not isinstance(target, dict):
        raise ValueError("target must be object")
    if "kind" not in target:
        raise ValueError("target kind missing")
    if "pk" not in target:
        raise ValueError("target pk missing")
    kind = target["kind"]
    pk = target["pk"]
    if not isinstance(kind, str):
        raise ValueError("target kind malformed")
    if kind not in ALLOWED_KINDS:
        raise ValueError("target kind malformed")
    if not _is_pk(pk):
        raise ValueError("target pk malformed")
    if "contacts" in payload:
        contacts = payload["contacts"]
    else:
        contacts = []
    if "deals" in payload:
        deals = payload["deals"]
    else:
        deals = []
    if "tasks" in payload:
        tasks = payload["tasks"]
    else:
        tasks = []
    if not isinstance(contacts, list):
        raise ValueError("contacts must be list")
    if not isinstance(deals, list):
        raise ValueError("deals must be list")
    if not isinstance(tasks, list):
        raise ValueError("tasks must be list")
    if len(contacts) > MAX_ENTRIES:
        raise ValueError("contacts too many")
    if len(deals) > MAX_ENTRIES:
        raise ValueError("deals too many")
    if len(tasks) > MAX_ENTRIES:
        raise ValueError("tasks too many")
    for entry in contacts:
        if not isinstance(entry, dict):
            raise ValueError("contact entry malformed")
        if "pk" not in entry:
            raise ValueError("contact pk missing")
        entry_pk = entry["pk"]
        if not _is_pk(entry_pk):
            raise ValueError("contact pk malformed")
        if "company_pk" in entry:
            company_pk = entry["company_pk"]
        else:
            company_pk = None
        if not _is_fk(company_pk):
            raise ValueError("contact company_pk malformed")
    for entry in deals:
        if not isinstance(entry, dict):
            raise ValueError("deal entry malformed")
        if "pk" not in entry:
            raise ValueError("deal pk missing")
        entry_pk = entry["pk"]
        if not _is_pk(entry_pk):
            raise ValueError("deal pk malformed")
        if "company_pk" in entry:
            company_pk = entry["company_pk"]
        else:
            company_pk = None
        if not _is_fk(company_pk):
            raise ValueError("deal company_pk malformed")
        if "contact_pk" in entry:
            contact_pk = entry["contact_pk"]
        else:
            contact_pk = None
        if not _is_fk(contact_pk):
            raise ValueError("deal contact_pk malformed")
    for entry in tasks:
        if not isinstance(entry, dict):
            raise ValueError("task entry malformed")
        if "pk" not in entry:
            raise ValueError("task pk missing")
        entry_pk = entry["pk"]
        if not _is_pk(entry_pk):
            raise ValueError("task pk malformed")
        if "deal_pk" in entry:
            deal_pk = entry["deal_pk"]
        else:
            deal_pk = None
        if not _is_fk(deal_pk):
            raise ValueError("task deal_pk malformed")
    affected_contacts = []
    affected_deals = []
    affected_tasks = []
    if kind == "company":
        contact_set = set()
        deal_set = set()
        for entry in contacts:
            if "company_pk" in entry:
                company_pk = entry["company_pk"]
            else:
                company_pk = None
            if company_pk == pk:
                contact_set.add(entry["pk"])
        for entry in deals:
            if "company_pk" in entry:
                company_pk = entry["company_pk"]
            else:
                company_pk = None
            if company_pk == pk:
                deal_set.add(entry["pk"])
        affected_contacts = sorted(contact_set)
        affected_deals = sorted(deal_set)
        affected_tasks = []
    if kind == "contact":
        deal_set = set()
        for entry in deals:
            if "contact_pk" in entry:
                contact_pk = entry["contact_pk"]
            else:
                contact_pk = None
            if contact_pk == pk:
                deal_set.add(entry["pk"])
        affected_contacts = []
        affected_deals = sorted(deal_set)
        affected_tasks = []
    if kind == "deal":
        task_set = set()
        for entry in tasks:
            if "deal_pk" in entry:
                deal_pk = entry["deal_pk"]
            else:
                deal_pk = None
            if deal_pk == pk:
                task_set.add(entry["pk"])
        affected_contacts = []
        affected_deals = []
        affected_tasks = sorted(task_set)
    if kind == "task":
        affected_contacts = []
        affected_deals = []
        affected_tasks = []
    contacts_count = len(affected_contacts)
    deals_count = len(affected_deals)
    tasks_count = len(affected_tasks)
    total_count = contacts_count + deals_count + tasks_count
    affected = {"contacts": affected_contacts, "deals": affected_deals, "tasks": affected_tasks}
    counts = {"contacts": contacts_count, "deals": deals_count, "tasks": tasks_count, "total": total_count}
    result_target = {"kind": kind, "pk": pk}
    result = {"target": result_target, "affected": affected, "counts": counts, "preserves_linked": True}
    return result
