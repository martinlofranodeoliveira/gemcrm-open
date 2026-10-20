import csv
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .models import Deal

STAGES = [
    ("new", "Novo"),
    ("qualified", "Qualificado"),
    ("proposal", "Proposta"),
    ("won", "Ganho"),
    ("lost", "Perdido"),
]

INVALID_MESSAGE = "Filtros inválidos. Use datas em AAAA-MM-DD, sem repetir parâmetros, com início menor ou igual ao fim."


def _strict_date(raw):
    if len(raw) != 10:
        return None
    try:
        raw.encode("ascii")
    except UnicodeEncodeError:
        return None
    if raw[4] != "-" or raw[7] != "-":
        return None
    for i in (0, 1, 2, 3, 5, 6, 8, 9):
        c = raw[i]
        if c < "0" or c > "9":
            return None
    year = int(raw[0:4])
    month = int(raw[5:7])
    day = int(raw[8:10])
    if year < 1 or year > 9999:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_pipeline_query(querydict):
    for key in querydict.keys():
        if key not in ("start", "end"):
            return (False, None, None)
    for key in ("start", "end"):
        if len(querydict.getlist(key)) > 1:
            return (False, None, None)
    raw_start = querydict.get("start")
    raw_end = querydict.get("end")
    start = None
    end = None
    if raw_start is not None and raw_start != "":
        start = _strict_date(raw_start)
        if start is None:
            return (False, None, None)
    if raw_end is not None and raw_end != "":
        end = _strict_date(raw_end)
        if end is None:
            return (False, None, None)
    if start is not None and end is not None and start > end:
        return (False, None, None)
    return (True, start, end)


def format_html_amount(value):
    q = value.quantize(Decimal("0.00"))
    return format(q, ".2f").replace(".", ",")


def format_csv_amount(value):
    q = value.quantize(Decimal("0.00"))
    return format(q, ".2f")


def collect_pipeline(user, start, end):
    qs = Deal.objects.filter(owner=user)
    if start is not None:
        qs = qs.filter(expected_close__gte=start)
    if end is not None:
        qs = qs.filter(expected_close__lte=end)
    counts = {k: 0 for k, _ in STAGES}
    sums = {k: Decimal("0.00") for k, _ in STAGES}
    total_count = 0
    total_sum = Decimal("0.00")
    for deal in qs:
        total_count += 1
        total_sum += deal.value
        if deal.stage in counts:
            counts[deal.stage] += 1
            sums[deal.stage] += deal.value
    return counts, sums, total_count, total_sum


def _export_suffix(start, end):
    parts = []
    if start is not None:
        parts.append("start=" + start.isoformat())
    if end is not None:
        parts.append("end=" + end.isoformat())
    if not parts:
        return ""
    return "?" + "&".join(parts)


@login_required
@require_GET
def pipeline_report(request):
    valid, start, end = parse_pipeline_query(request.GET)
    if not valid:
        return render(request, "crm/pipeline_report.html", {"valid": False}, status=400)
    counts, sums, total_count, total_sum = collect_pipeline(request.user, start, end)
    rows = []
    for key, label in STAGES:
        rows.append(
            {
                "key": key,
                "label": label,
                "count": str(counts[key]),
                "amount_html": format_html_amount(sums[key]),
            }
        )
    context = {
        "valid": True,
        "rows": rows,
        "total_count": str(total_count),
        "total_html": format_html_amount(total_sum),
        "start_value": start.isoformat() if start is not None else "",
        "end_value": end.isoformat() if end is not None else "",
        "export_suffix": _export_suffix(start, end),
        "is_empty": total_count == 0,
    }
    return render(request, "crm/pipeline_report.html", context)


@login_required
@require_GET
def pipeline_report_export(request):
    valid, start, end = parse_pipeline_query(request.GET)
    if not valid:
        return HttpResponse(INVALID_MESSAGE, content_type="text/plain; charset=utf-8", status=400)
    counts, sums, total_count, total_sum = collect_pipeline(request.user, start, end)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="gemcrm-pipeline.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, lineterminator="\r\n")
    writer.writerow(["Etapa", "Oportunidades", "Valor (R$)"])
    for key, label in STAGES:
        writer.writerow([label, str(counts[key]), format_csv_amount(sums[key])])
    writer.writerow(["Total", str(total_count), format_csv_amount(total_sum)])
    return response
