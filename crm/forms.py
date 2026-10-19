from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Company, Contact, Deal, Task


CONTACT_IMPORT_MAX_BYTES = 256 * 1024


class ContactImportUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="Arquivo CSV",
        help_text="UTF-8, até 256 KiB e 500 contatos. Nenhum contato é salvo na prévia.",
        widget=forms.ClearableFileInput(attrs={"accept": ".csv,text/csv"}),
    )

    def clean_csv_file(self):
        uploaded = self.cleaned_data["csv_file"]
        if uploaded.size > CONTACT_IMPORT_MAX_BYTES:
            raise forms.ValidationError("O arquivo deve ter no máximo 256 KiB.")
        content = uploaded.read(CONTACT_IMPORT_MAX_BYTES + 1)
        if len(content) > CONTACT_IMPORT_MAX_BYTES:
            raise forms.ValidationError("O arquivo deve ter no máximo 256 KiB.")
        try:
            return content.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise forms.ValidationError("Envie um arquivo CSV codificado em UTF-8.") from None


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
