import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.db.models import Q, Sum
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .contact_import_workflow import (
    DRAFT_SESSION_KEY, MAX_ROWS, PREVIEW_SECONDS, ImportRejected, PreviewUnavailable,
    begin_preview, confirm_contacts, database_sessions_enabled, preview_contacts, save_preview,
)
from .forms import CONTACT_IMPORT_MAX_BYTES, CompanyForm, ContactForm, ContactImportUploadForm, DealForm, SignupForm, TaskForm
from .models import Company, Contact, Deal, Task


def signup(request):
    if request.user.is_authenticated:
        return redirect("crm:dashboard")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("crm:dashboard")
    return render(request, "registration/signup.html", {"form": form})


@login_required
def dashboard(request):
    deals = Deal.objects.filter(owner=request.user).select_related("company", "contact")
    open_deals = deals.exclude(stage__in=[Deal.Stage.WON, Deal.Stage.LOST])
    context = {
        "company_count": Company.objects.filter(owner=request.user).count(),
        "contact_count": Contact.objects.filter(owner=request.user).count(),
        "open_deal_count": open_deals.count(),
        "pipeline_value": open_deals.aggregate(total=Sum("value"))["total"] or Decimal("0.00"),
        "due_tasks": Task.objects.filter(owner=request.user, completed=False, due_date__lte=timezone.localdate()).select_related("deal")[:6],
        "recent_deals": deals[:6],
        "today": timezone.localdate(),
    }
    return render(request, "crm/dashboard.html", context)


@login_required
def companies(request):
    q = request.GET.get("q", "").strip()[:200]
    items = Company.objects.filter(owner=request.user)
    if q:
        items = items.filter(Q(name__icontains=q) | Q(website__icontains=q) | Q(notes__icontains=q))
    return render(request, "crm/companies.html", {"items": items, "q": q})


@login_required
def contacts(request):
    q = request.GET.get("q", "").strip()[:200]
    items = _contacts_for_search(request.user, q)
    return render(request, "crm/contacts.html", {"items": items, "q": q})


def _render_contact_import(request, form=None, *, status=200, **context):
    return render(request, "crm/contact_import.html", {
        "form": form if form is not None else ContactImportUploadForm(),
        "preview": None,
        "preview_token": None,
        "confirm_error": "",
        "max_bytes": CONTACT_IMPORT_MAX_BYTES,
        "max_rows": MAX_ROWS,
        "preview_minutes": PREVIEW_SECONDS // 60,
        "back_url": reverse("crm:contacts"),
        **context,
    }, status=status)


@login_required
@require_http_methods(["GET", "POST"])
def contact_import(request):
    if request.method == "GET":
        return _render_contact_import(request)
    # A new attempt always invalidates the preceding preview, even if invalid.
    request.session.pop(DRAFT_SESSION_KEY, None)
    if not database_sessions_enabled():
        form = ContactImportUploadForm(data={})
        form.add_error(None, "A importação requer sessões armazenadas no servidor pelo banco de dados.")
        return _render_contact_import(request, form)
    try:
        attempt_token = begin_preview(request.session, request.user)
    except DatabaseError:
        return _render_contact_import(request, confirm_error="Não foi possível iniciar a prévia. Tente novamente.")
    form = ContactImportUploadForm(request.POST, request.FILES)
    if (
        set(request.POST) - {"csrfmiddlewaretoken"}
        or set(request.FILES) - {"csv_file"}
        or len(request.FILES.getlist("csv_file")) != 1
    ):
        form.add_error(None, "Envie somente um arquivo CSV pelo formulário de importação.")
        return _render_contact_import(request, form)
    if not form.is_valid():
        return _render_contact_import(request, form)
    text = form.cleaned_data["csv_file"]
    try:
        preview = preview_contacts(request.user, text)
    except DatabaseError:
        return _render_contact_import(request, form, confirm_error="Não foi possível validar o cadastro agora. Tente novamente.")
    try:
        token = save_preview(request.session, request.user, text, attempt_token=attempt_token) if preview["valid"] else None
    except (PreviewUnavailable, DatabaseError):
        return _render_contact_import(
            request, form, preview=preview,
            confirm_error="Outro envio substituiu esta prévia ou o cadastro está ocupado. Envie o arquivo novamente.",
        )
    return _render_contact_import(request, form, preview=preview, preview_token=token)


@login_required
@require_POST
def contact_import_confirm(request):
    allowed_fields = {"csrfmiddlewaretoken", "preview_token"}
    if request.FILES or set(request.POST) - allowed_fields or len(request.POST.getlist("preview_token")) != 1:
        return _render_contact_import(request, status=400, confirm_error="Confirmação inválida. Envie o arquivo novamente.")
    try:
        count = confirm_contacts(request.session, request.user, request.POST["preview_token"])
    except PreviewUnavailable:
        return _render_contact_import(request, confirm_error="A prévia expirou ou já foi usada. Envie o arquivo novamente.")
    except ImportRejected as error:
        return _render_contact_import(
            request, preview=error.preview,
            confirm_error="O cadastro mudou ou há dados inválidos. Revise a prévia e envie o arquivo novamente.",
        )
    except DatabaseError:
        return _render_contact_import(
            request, confirm_error="A importação não foi salva. Nenhum contato deste lote foi criado. Tente novamente.",
        )
    messages.success(request, f"Importação concluída: {count} contato(s) criado(s).")
    return redirect("crm:contacts")


def _contacts_for_search(owner, q):
    items = Contact.objects.filter(owner=owner).select_related("company")
    if q:
        items = items.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q) | Q(company__name__icontains=q))
    return items


@login_required
def deals(request):
    q = request.GET.get("q", "").strip()[:200]
    items = Deal.objects.filter(owner=request.user).select_related("company", "contact")
    if q:
        items = items.filter(Q(title__icontains=q) | Q(company__name__icontains=q) | Q(contact__name__icontains=q))
    grouped = {stage: [] for stage, _ in Deal.Stage.choices}
    for item in items:
        grouped[item.stage].append(item)
    columns = [{"value": stage, "label": label, "deals": grouped[stage]} for stage, label in Deal.Stage.choices]
    return render(request, "crm/deals.html", {"columns": columns, "q": q, "stages": Deal.Stage.choices})


@login_required
def tasks(request):
    q = request.GET.get("q", "").strip()[:200]
    items = Task.objects.filter(owner=request.user).select_related("deal")
    if q:
        items = items.filter(Q(title__icontains=q) | Q(deal__title__icontains=q))
    status = request.GET.get("status", "all")
    if status == "open":
        items = items.filter(completed=False)
    elif status == "completed":
        items = items.filter(completed=True)
    elif status == "overdue":
        items = items.filter(completed=False, due_date__lt=timezone.localdate())
    elif status == "today":
        items = items.filter(completed=False, due_date=timezone.localdate())
    elif status == "upcoming":
        items = items.filter(completed=False, due_date__gt=timezone.localdate())
    else:
        status = "all"
    return render(request, "crm/tasks.html", {"items": items, "q": q, "status": status, "today": timezone.localdate()})


def _edit_record(request, model, form_class, list_name, title, pk=None):
    instance = get_object_or_404(model, pk=pk, owner=request.user) if pk is not None else None
    form = form_class(request.POST or None, instance=instance, owner=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Registro salvo.")
        return redirect(f"crm:{list_name}")
    return render(request, "crm/form.html", {
        "form": form, "title": title, "back_url": reverse(f"crm:{list_name}"),
        "delete_url": reverse(f"crm:{model._meta.model_name}_delete", args=[pk]) if instance else None,
    })


def _delete_record(request, model, list_name, title, pk):
    record = get_object_or_404(model, pk=pk, owner=request.user)
    if request.method == "POST":
        record.delete()
        messages.success(request, "Registro excluído.")
        return redirect(f"crm:{list_name}")
    return render(request, "crm/confirm_delete.html", {"object": record, "title": title, "back_url": reverse(f"crm:{list_name}")})


@login_required
def company_create(request):
    return _edit_record(request, Company, CompanyForm, "companies", "Nova empresa")


@login_required
def company_update(request, pk):
    return _edit_record(request, Company, CompanyForm, "companies", "Editar empresa", pk)


@login_required
def company_delete(request, pk):
    return _delete_record(request, Company, "companies", "Excluir empresa", pk)


@login_required
def contact_create(request):
    return _edit_record(request, Contact, ContactForm, "contacts", "Novo contato")


@login_required
def contact_update(request, pk):
    return _edit_record(request, Contact, ContactForm, "contacts", "Editar contato", pk)


@login_required
def contact_delete(request, pk):
    return _delete_record(request, Contact, "contacts", "Excluir contato", pk)


@login_required
def deal_create(request):
    return _edit_record(request, Deal, DealForm, "deals", "Nova oportunidade")


@login_required
def deal_update(request, pk):
    return _edit_record(request, Deal, DealForm, "deals", "Editar oportunidade", pk)


@login_required
def deal_delete(request, pk):
    return _delete_record(request, Deal, "deals", "Excluir oportunidade", pk)


@login_required
def task_create(request):
    return _edit_record(request, Task, TaskForm, "tasks", "Nova tarefa")


@login_required
def task_update(request, pk):
    return _edit_record(request, Task, TaskForm, "tasks", "Editar tarefa", pk)


@login_required
def task_delete(request, pk):
    return _delete_record(request, Task, "tasks", "Excluir tarefa", pk)


@login_required
@require_POST
def deal_stage(request, pk):
    deal = get_object_or_404(Deal, pk=pk, owner=request.user)
    stage = request.POST.get("stage")
    if stage not in Deal.Stage.values:
        return HttpResponseBadRequest("Etapa inválida.")
    deal.stage = stage
    deal.save(update_fields=["stage", "updated_at"])
    messages.success(request, "Etapa atualizada.")
    return redirect("crm:deals")


@login_required
@require_POST
def task_toggle(request, pk):
    task = get_object_or_404(Task, pk=pk, owner=request.user)
    task.completed = not task.completed
    task.save(update_fields=["completed", "updated_at"])
    return redirect("crm:tasks")


def _safe_csv_cell(value):
    """Treat leading spreadsheet formulas as literal user text on export."""
    value = str(value or "")
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


@login_required
def contact_export(request):
    q = request.GET.get("q", "").strip()[:200]
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="gemcrm-contatos.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["Nome", "E-mail", "Telefone", "Empresa", "Observações"])
    for contact in _contacts_for_search(request.user, q).iterator():
        writer.writerow([_safe_csv_cell(value) for value in [contact.name, contact.email, contact.phone, contact.company.name if contact.company else "", contact.notes]])
    return response
