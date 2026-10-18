from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Company, Contact, Deal, Task


class SignupForm(UserCreationForm):
    email = forms.EmailField(label="E-mail", required=False)

    class Meta(UserCreationForm.Meta):
        fields = ("username", "email")


class OwnedModelForm(forms.ModelForm):
    """All related objects are selected exclusively from the current account."""

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.owner = owner
        for field in self.fields.values():
            if isinstance(field, forms.ModelChoiceField):
                field.queryset = field.queryset.filter(owner=owner)


class CompanyForm(OwnedModelForm):
    class Meta:
        model = Company
        fields = ["name", "website", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}


class ContactForm(OwnedModelForm):
    class Meta:
        model = Contact
        fields = ["name", "email", "phone", "company", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 4})}


class DealForm(OwnedModelForm):
    class Meta:
        model = Deal
        fields = ["title", "company", "contact", "value", "stage", "expected_close", "notes"]
        widgets = {
            "expected_close": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }


class TaskForm(OwnedModelForm):
    class Meta:
        model = Task
        fields = ["title", "deal", "due_date", "completed"]
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}
