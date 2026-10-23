# Deal stage transition guard core.
# Pure deterministic validator for five-stage pipeline moves.
STAGES = ("new", "qualified", "proposal", "won", "lost")
OPEN = ("new", "qualified", "proposal")
CLOSED = ("won", "lost")


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    if "current_stage" not in payload:
        raise ValueError("current_stage is required")
    if "next_stage" not in payload:
        raise ValueError("next_stage is required")
    current_stage = payload["current_stage"]
    next_stage = payload["next_stage"]
    if type(current_stage) is not str:
        raise ValueError("current_stage must be a string")
    if type(next_stage) is not str:
        raise ValueError("next_stage must be a string")
    if current_stage not in STAGES:
        raise ValueError("unknown current_stage")
    if next_stage not in STAGES:
        raise ValueError("unknown next_stage")
    if current_stage == next_stage:
        changed = False
    else:
        changed = True
    if current_stage in CLOSED:
        terminal = True
    else:
        terminal = False
    if not changed:
        valid = True
    else:
        if current_stage in OPEN:
            valid = True
        else:
            valid = False
    if changed and valid and next_stage in CLOSED:
        close = True
    else:
        close = False
    if not changed:
        reason = "noop"
    else:
        if not valid:
            reason = "terminal_blocked"
        else:
            if next_stage in CLOSED:
                reason = "close"
            else:
                reason = "progress"
    return {"current_stage": current_stage, "next_stage": next_stage, "valid": valid, "changed": changed, "terminal": terminal, "close": close, "reason": reason}
