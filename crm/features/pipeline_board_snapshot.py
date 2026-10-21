"""Pure snapshot for sales pipeline board."""
_STAGE_ORDER = ("new", "qualified", "proposal", "won", "lost")
_LABEL_NEW = "Novo"
_LABEL_QUALIFIED = "Qualificado"
_LABEL_PROPOSAL = "Proposta"
_LABEL_WON = "Ganho"
_LABEL_LOST = "Perdido"
_MAX_DEALS = 2000
_MAX_PK = 9007199254740991
_MAX_CENTS = 99999999999999
_MAX_TITLE_LEN = 180
_MIN_PK = 1
_MIN_TITLE_LEN = 1

def _format_csv(cents):
    whole = cents // 100
    rest = cents - whole * 100
    if rest < 10:
        tail = "0" + str(rest)
    else:
        tail = str(rest)
    return str(whole) + "." + tail

def _format_display(cents):
    whole = cents // 100
    rest = cents - whole * 100
    if rest < 10:
        tail = "0" + str(rest)
    else:
        tail = str(rest)
    return "R$ " + str(whole) + "," + tail

def _parse_value_to_cents(value):
    if type(value) is not str:
        raise ValueError("value must be str")
    if len(value) == 0:
        raise ValueError("value empty")
    dots = 0
    for ch in value:
        if ch == ".":
            dots = dots + 1
        else:
            if ch < "0" or ch > "9":
                raise ValueError("value chars")
    if dots > 1:
        raise ValueError("value dots")
    if dots == 0:
        int_part = value
        frac_part = ""
        frac_len = 0
    else:
        parts = value.split(".")
        if len(parts) != 2:
            raise ValueError("value dot")
        int_part = parts[0]
        frac_part = parts[1]
        frac_len = len(frac_part)
        if len(int_part) == 0:
            raise ValueError("value int")
        if frac_len == 0 or frac_len > 2:
            raise ValueError("value frac")
    if len(int_part) == 0:
        raise ValueError("value int")
    if len(int_part) > 1 and int_part[0] == "0":
        raise ValueError("value zeros")
    if dots == 0:
        cents = int(int_part) * 100
    else:
        if frac_len == 1:
            cents = int(int_part) * 100 + int(frac_part) * 10
        else:
            cents = int(int_part) * 100 + int(frac_part)
    if cents > _MAX_CENTS:
        raise ValueError("value range")
    return cents

def _label_for_stage(stage):
    if stage == "new":
        return _LABEL_NEW
    if stage == "qualified":
        return _LABEL_QUALIFIED
    if stage == "proposal":
        return _LABEL_PROPOSAL
    if stage == "won":
        return _LABEL_WON
    return _LABEL_LOST

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    if "deals" in payload:
        deals_in = payload["deals"]
    else:
        deals_in = []
    if not isinstance(deals_in, list):
        raise ValueError("deals must be list")
    if len(deals_in) > _MAX_DEALS:
        raise ValueError("deals limit")
    new_list = []
    qualified_list = []
    proposal_list = []
    won_list = []
    lost_list = []
    new_total = 0
    qualified_total = 0
    proposal_total = 0
    won_total = 0
    lost_total = 0
    grand_total = 0
    for entry in deals_in:
        if not isinstance(entry, dict):
            raise ValueError("deal must be object")
        if "pk" in entry:
            pk = entry["pk"]
        else:
            raise ValueError("pk missing")
        if "title" in entry:
            title = entry["title"]
        else:
            raise ValueError("title missing")
        if "stage" in entry:
            stage = entry["stage"]
        else:
            raise ValueError("stage missing")
        if "value" in entry:
            value = entry["value"]
        else:
            raise ValueError("value missing")
        if type(pk) is not int:
            raise ValueError("pk type")
        if pk < _MIN_PK or pk > _MAX_PK:
            raise ValueError("pk range")
        if type(title) is not str:
            raise ValueError("title type")
        if len(title) < _MIN_TITLE_LEN or len(title) > _MAX_TITLE_LEN:
            raise ValueError("title range")
        if type(stage) is not str:
            raise ValueError("stage type")
        if stage != "new" and stage != "qualified" and stage != "proposal" and stage != "won" and stage != "lost":
            raise ValueError("stage value")
        cents = _parse_value_to_cents(value)
        csv_text = _format_csv(cents)
        display_text = _format_display(cents)
        built = {"pk": pk, "title": title, "stage": stage, "value_cents": cents, "value_csv": csv_text, "value_display": display_text}
        if stage == "new":
            new_list.append(built)
            new_total = new_total + cents
        else:
            if stage == "qualified":
                qualified_list.append(built)
                qualified_total = qualified_total + cents
            else:
                if stage == "proposal":
                    proposal_list.append(built)
                    proposal_total = proposal_total + cents
                else:
                    if stage == "won":
                        won_list.append(built)
                        won_total = won_total + cents
                    else:
                        lost_list.append(built)
                        lost_total = lost_total + cents
        grand_total = grand_total + cents
    new_csv = _format_csv(new_total)
    new_display = _format_display(new_total)
    qualified_csv = _format_csv(qualified_total)
    qualified_display = _format_display(qualified_total)
    proposal_csv = _format_csv(proposal_total)
    proposal_display = _format_display(proposal_total)
    won_csv = _format_csv(won_total)
    won_display = _format_display(won_total)
    lost_csv = _format_csv(lost_total)
    lost_display = _format_display(lost_total)
    grand_csv = _format_csv(grand_total)
    grand_display = _format_display(grand_total)
    total_n = len(deals_in)
    columns = {
        "new": {"label": _LABEL_NEW, "count": len(new_list), "total_cents": new_total, "total_csv": new_csv, "total_display": new_display, "deals": new_list},
        "qualified": {"label": _LABEL_QUALIFIED, "count": len(qualified_list), "total_cents": qualified_total, "total_csv": qualified_csv, "total_display": qualified_display, "deals": qualified_list},
        "proposal": {"label": _LABEL_PROPOSAL, "count": len(proposal_list), "total_cents": proposal_total, "total_csv": proposal_csv, "total_display": proposal_display, "deals": proposal_list},
        "won": {"label": _LABEL_WON, "count": len(won_list), "total_cents": won_total, "total_csv": won_csv, "total_display": won_display, "deals": won_list},
        "lost": {"label": _LABEL_LOST, "count": len(lost_list), "total_cents": lost_total, "total_csv": lost_csv, "total_display": lost_display, "deals": lost_list}
    }
    grand = {"count": total_n, "total_cents": grand_total, "total_csv": grand_csv, "total_display": grand_display}
    return {"deal_count": total_n, "columns": columns, "grand": grand}
