"""Populate an explicitly selected, empty account with fictional CRM examples."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from crm.models import Company, Contact, Deal, Task


class Command(BaseCommand):
    help = "Adiciona dados fictícios a uma conta existente e vazia. Não cria senhas."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Conta existente que receberá os exemplos.")

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            owner = get_user_model().objects.get(username=options["username"])
        except get_user_model().DoesNotExist as exc:
            raise CommandError("Crie a conta antes de adicionar dados fictícios.") from exc
        if any(model.objects.filter(owner=owner).exists() for model in [Company, Contact, Deal, Task]):
            raise CommandError("A conta precisa estar vazia para não misturar exemplos com dados existentes.")

        companies = [
            Company.objects.create(owner=owner, name=name, website="https://example.com", notes="Empresa fictícia para demonstração.")
            for name in ["Ateliê Horizonte", "Café Aurora", "Estúdio Raiz", "Oficina Brisa"]
        ]
        contacts = [
            Contact.objects.create(owner=owner, name=name, email=email, company=companies[index], notes="Contato fictício para demonstração.")
            for name, email, index in [
                ("Ana Exemplo", "ana@example.com", 0),
                ("Bruno Exemplo", "bruno@example.com", 1),
                ("Clara Exemplo", "clara@example.com", 2),
                ("Diego Exemplo", "diego@example.com", 3),
            ]
        ]
        today = timezone.localdate()
        deals = []
        for title, value, stage, index, days in [
            ("Novo site institucional", "4800.00", Deal.Stage.PROPOSAL, 0, 7),
            ("Programa de fidelidade", "2400.00", Deal.Stage.QUALIFIED, 1, 14),
            ("Identidade visual", "3600.00", Deal.Stage.NEW, 2, 21),
            ("Agendamento digital", "1800.00", Deal.Stage.NEW, 3, 10),
            ("Catálogo de produtos", "2200.00", Deal.Stage.WON, 0, -5),
            ("Campanha de inverno", "1500.00", Deal.Stage.LOST, 1, -8),
        ]:
            deals.append(Deal.objects.create(owner=owner, title=title, company=companies[index], contact=contacts[index], value=Decimal(value), stage=stage, expected_close=today + timedelta(days=days), notes="Oportunidade fictícia para demonstração."))
        for title, days, deal_index, completed in [
            ("Enviar proposta do site", 0, 0, False),
            ("Confirmar reunião com o café", -1, 1, False),
            ("Preparar referências visuais", 2, 2, False),
            ("Mapear fluxo de agendamento", 4, 3, False),
            ("Entregar catálogo aprovado", -3, 4, True),
        ]:
            Task.objects.create(owner=owner, title=title, due_date=today + timedelta(days=days), deal=deals[deal_index], completed=completed)
        self.stdout.write(self.style.SUCCESS("Dados fictícios criados: 4 empresas, 4 contatos, 6 oportunidades e 5 tarefas."))
