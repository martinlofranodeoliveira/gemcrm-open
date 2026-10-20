from django.urls import path

from . import pipeline_reports
from . import views

app_name = "crm"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("companies/", views.companies, name="companies"),
    path("companies/new/", views.company_create, name="company_create"),
    path("companies/<int:pk>/edit/", views.company_update, name="company_update"),
    path("companies/<int:pk>/delete/", views.company_delete, name="company_delete"),
    path("contacts/", views.contacts, name="contacts"),
    path("contacts/new/", views.contact_create, name="contact_create"),
    path("contacts/export/", views.contact_export, name="contact_export"),
    path("contacts/import/", views.contact_import, name="contact_import"),
    path("contacts/import/confirm/", views.contact_import_confirm, name="contact_import_confirm"),
    path("contacts/<int:pk>/edit/", views.contact_update, name="contact_update"),
    path("contacts/<int:pk>/delete/", views.contact_delete, name="contact_delete"),
    path("deals/", views.deals, name="deals"),
    path("deals/new/", views.deal_create, name="deal_create"),
    path("deals/<int:pk>/edit/", views.deal_update, name="deal_update"),
    path("deals/<int:pk>/delete/", views.deal_delete, name="deal_delete"),
    path("deals/<int:pk>/stage/", views.deal_stage, name="deal_stage"),
    path("tasks/", views.tasks, name="tasks"),
    path("tasks/new/", views.task_create, name="task_create"),
    path("tasks/<int:pk>/edit/", views.task_update, name="task_update"),
    path("tasks/<int:pk>/delete/", views.task_delete, name="task_delete"),
    path("tasks/<int:pk>/toggle/", views.task_toggle, name="task_toggle"),
    path("reports/pipeline/", pipeline_reports.pipeline_report, name="pipeline_report"),
    path("reports/pipeline/export/", pipeline_reports.pipeline_report_export, name="pipeline_report_export"),
]
