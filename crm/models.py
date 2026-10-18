from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class OwnedRecord(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def validate_related_owners(self, *field_names):
        errors = {}
        for name in field_names:
            related = getattr(self, name, None)
            if related is not None and related.owner_id != self.owner_id:
                errors[name] = "Escolha um registro da sua conta."
        if errors:
            raise ValidationError(errors)


class Company(OwnedRecord):
    name = models.CharField("Nome", max_length=180)
    website = models.URLField("Site", blank=True)
    notes = models.TextField("Observações", blank=True)

    class Meta:
        ordering = ["name", "pk"]
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return self.name


class Contact(OwnedRecord):
    name = models.CharField("Nome", max_length=180)
    email = models.EmailField("E-mail", blank=True)
    phone = models.CharField("Telefone", max_length=40, blank=True)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Empresa")
    notes = models.TextField("Observações", blank=True)

    class Meta:
        ordering = ["name", "pk"]
        verbose_name = "Contato"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        self.validate_related_owners("company")


class Deal(OwnedRecord):
    class Stage(models.TextChoices):
        NEW = "new", "Novo"
        QUALIFIED = "qualified", "Qualificado"
        PROPOSAL = "proposal", "Proposta"
        WON = "won", "Ganho"
        LOST = "lost", "Perdido"

    title = models.CharField("Título", max_length=180)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Empresa")
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Contato")
    value = models.DecimalField("Valor (R$)", max_digits=14, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0.00"))])
    stage = models.CharField("Etapa", max_length=12, choices=Stage.choices, default=Stage.NEW)
    expected_close = models.DateField("Previsão de fechamento", blank=True, null=True)
    notes = models.TextField("Observações", blank=True)

    class Meta:
        ordering = ["-updated_at", "-pk"]
        verbose_name = "Oportunidade"
        constraints = [models.CheckConstraint(condition=models.Q(value__gte=0), name="deal_value_nonnegative")]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        self.validate_related_owners("company", "contact")


class Task(OwnedRecord):
    title = models.CharField("Título", max_length=180)
    deal = models.ForeignKey(Deal, on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Oportunidade")
    due_date = models.DateField("Vencimento")
    completed = models.BooleanField("Concluída", default=False)

    class Meta:
        ordering = ["completed", "due_date", "pk"]
        verbose_name = "Tarefa"

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        self.validate_related_owners("deal")
