"""deal company contact link check"""
_MAX_PK = 9007199254740991
_MIN_PK = 1
_MAX_ITEMS = 50
_MAX_TEXT = 180
_ALLOWED_STAGES = ("new", "qualified", "proposal", "won", "lost")

def _check_pk(value):
    if type(value) is not int:
        raise ValueError("bad pk")
    if value < 1:
        raise ValueError("bad pk")
    if value > 9007199254740991:
        raise ValueError("bad pk")
    return value

def _check_text(value):
    if type(value) is not str:
        raise ValueError("bad text")
    if len(value) < 1:
        raise ValueError("bad text")
    if len(value) > 180:
        raise ValueError("bad text")
    return value

def _check_stage(value):
    if type(value) is not str:
        raise ValueError("bad stage")
    if value not in _ALLOWED_STAGES:
        raise ValueError("bad stage")
    return value

def _check_nullable_pk(value):
    if value is None:
        return None
    if type(value) is not int:
        raise ValueError("bad link")
    if value < 1:
        raise ValueError("bad link")
    if value > 9007199254740991:
        raise ValueError("bad link")
    return value

def _get_list(payload, key):
    if key not in payload:
        return []
    value = payload[key]
    if value is None:
        raise ValueError("bad list")
    if not isinstance(value, list):
        raise ValueError("bad list")
    if len(value) > 50:
        raise ValueError("bad list")
    return value

def run_feature(payload):
    if payload is None:
        raise ValueError("bad payload")
    if not isinstance(payload, dict):
        raise ValueError("bad payload")
    companies = _get_list(payload, "companies")
    contacts = _get_list(payload, "contacts")
    deals_in = _get_list(payload, "deals")
    company_seen = {}
    contact_map = {}
    deal_seen = {}
    for item in companies:
        if not isinstance(item, dict):
            raise ValueError("bad company")
        if "pk" not in item:
            raise ValueError("bad company")
        if "name" not in item:
            raise ValueError("bad company")
        pk_value = _check_pk(item["pk"])
        name_value = _check_text(item["name"])
        if pk_value in company_seen:
            raise ValueError("bad company")
        company_seen[pk_value] = True
    for item in contacts:
        if not isinstance(item, dict):
            raise ValueError("bad contact")
        if "pk" not in item:
            raise ValueError("bad contact")
        if "name" not in item:
            raise ValueError("bad contact")
        if "company_pk" not in item:
            raise ValueError("bad contact")
        pk_value = _check_pk(item["pk"])
        name_value = _check_text(item["name"])
        company_value = _check_nullable_pk(item["company_pk"])
        if pk_value in contact_map:
            raise ValueError("bad contact")
        contact_map[pk_value] = company_value
    out_deals = []
    linked_count = 0
    mismatched_count = 0
    dangling_company_count = 0
    dangling_contact_count = 0
    for item in deals_in:
        if not isinstance(item, dict):
            raise ValueError("bad deal")
        if "pk" not in item:
            raise ValueError("bad deal")
        if "title" not in item:
            raise ValueError("bad deal")
        if "stage" not in item:
            raise ValueError("bad deal")
        if "company_pk" not in item:
            raise ValueError("bad deal")
        if "contact_pk" not in item:
            raise ValueError("bad deal")
        pk_value = _check_pk(item["pk"])
        title_value = _check_text(item["title"])
        stage_value = _check_stage(item["stage"])
        company_value = _check_nullable_pk(item["company_pk"])
        contact_value = _check_nullable_pk(item["contact_pk"])
        if pk_value in deal_seen:
            raise ValueError("bad deal")
        deal_seen[pk_value] = True
        if company_value is None:
            company_exists = True
        else:
            if company_value in company_seen:
                company_exists = True
            else:
                company_exists = False
        if contact_value is None:
            contact_exists = True
        else:
            if contact_value in contact_map:
                contact_exists = True
            else:
                contact_exists = False
        if contact_value is None:
            company_match = True
        else:
            if contact_exists:
                mapped_value = contact_map[contact_value]
                if company_value == mapped_value:
                    company_match = True
                else:
                    company_match = False
            else:
                company_match = False
        entry = {"pk": pk_value, "title": title_value, "stage": stage_value, "company_pk": company_value, "contact_pk": contact_value, "company_exists": company_exists, "contact_exists": contact_exists, "company_match": company_match}
        out_deals = out_deals + [entry]
        if contact_value is None:
            pass
        else:
            if contact_exists:
                linked_count = linked_count + 1
                wanted = contact_map[contact_value]
                if company_value == wanted:
                    pass
                else:
                    mismatched_count = mismatched_count + 1
            else:
                dangling_contact_count = dangling_contact_count + 1
        if company_value is None:
            pass
        else:
            if company_value in company_seen:
                pass
            else:
                dangling_company_count = dangling_company_count + 1
    result = {"deal_count": len(deals_in), "linked_count": linked_count, "mismatched_count": mismatched_count, "dangling_company_count": dangling_company_count, "dangling_contact_count": dangling_contact_count, "deals": out_deals}
    return result
