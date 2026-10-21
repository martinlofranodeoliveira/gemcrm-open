"""Spreadsheet-safe CSV cell guard core.

Pure deterministic snapshot formula-prefix mitigation. No I/O,
env, time, randomness, callbacks, ownership checks, DB queries,
CSV handling, or clock reads. Caller stringifies values, filters
ownership, and quotes CSV separately.
"""
MAX_CELLS = 2000
MAX_CELL_LENGTH = 5000
TRIGGER_CHARS = ("=", "+", "-", "@", "|", "%")
STRIP_CHARS = " \t\r\n"
QUOTE_PREFIX = "'"


def _strip_leading(value):
    """Remove leading SP, TAB, CR, LF only."""
    pos = 0
    total = len(value)
    while pos < total:
        current = value[pos]
        if current in STRIP_CHARS:
            pos = pos + 1
        else:
            break
    return value[pos:]


def _is_flagged(stripped):
    """Return True when stripped starts with a trigger character."""
    if len(stripped) == 0:
        return False
    first = stripped[0]
    if first in TRIGGER_CHARS:
        return True
    return False


def run_feature(payload):
    """Guard cells against spreadsheet formula prefixes.

    Accepts an object with optional list key cells. Returns dict
    with total_count, flagged_count, and results list.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    if "cells" in payload:
        cells = payload["cells"]
    else:
        cells = []
    if not isinstance(cells, list):
        raise ValueError("cells must be a list")
    if len(cells) > MAX_CELLS:
        raise ValueError("cells exceeds limit of 2000")
    total = len(cells)
    results = []
    flagged_count = 0
    index = 0
    while index < total:
        cell = cells[index]
        if not isinstance(cell, str):
            raise ValueError("each cell must be str")
        if len(cell) > MAX_CELL_LENGTH:
            raise ValueError("cell exceeds length of 5000")
        stripped = _strip_leading(cell)
        flagged = _is_flagged(stripped)
        if flagged:
            safe = QUOTE_PREFIX + cell[:]
        else:
            safe = cell[:]
        source = cell[:]
        entry = {"index": index, "source": source, "safe": safe, "flagged": flagged}
        results = results + [entry]
        if flagged:
            flagged_count = flagged_count + 1
        index = index + 1
    return {"total_count": total, "flagged_count": flagged_count, "results": results}
