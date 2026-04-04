"""Factories compartilhadas para reduzir boilerplate dos testes do projeto."""

from __future__ import annotations

from datetime import datetime

import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

from core.models import AuditLog, Module

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """Factory canônica de usuários para testes unitários, HTML e E2E."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.LazyAttribute(lambda user: f"{user.username}@example.com")
    first_name = ""
    last_name = ""
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(self, create: bool, extracted: str | None, **kwargs: object) -> None:
        """Garante hash real da senha sem depender do save implícito do factory_boy."""

        raw_password = extracted or "SenhaSegura@123"
        user = self
        user_obj = user if isinstance(user, User) else None
        if user_obj is None:
            return
        user_obj.set_password(raw_password)
        if create:
            user_obj.save(update_fields=["password"])

    @factory.post_generation
    def groups(self, create: bool, extracted: list[Group] | None, **kwargs: object) -> None:
        """Relaciona grupos quando o chamador os informar explicitamente."""

        if not create or not extracted:
            return
        self.groups.add(*extracted)

    @factory.post_generation
    def user_permissions(
        self,
        create: bool,
        extracted: list[Permission] | None,
        **kwargs: object,
    ) -> None:
        """Relaciona permissões diretas quando o chamador as informar."""

        if not create or not extracted:
            return
        self.user_permissions.add(*extracted)


class StaffUserFactory(UserFactory):
    """Atalho para contas administrativas simples."""

    is_staff = True


class SuperUserFactory(StaffUserFactory):
    """Atalho para contas `superuser` usadas em cenários privilegiados."""

    is_superuser = True
    is_staff = True


class GroupFactory(factory.django.DjangoModelFactory):
    """Factory canônica de grupos reutilizáveis nos testes."""

    class Meta:
        model = Group
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f"Grupo {n}")

    @factory.post_generation
    def permissions(
        self,
        create: bool,
        extracted: list[Permission] | None,
        **kwargs: object,
    ) -> None:
        """Relaciona permissões do grupo quando informadas pelo teste."""

        if not create or not extracted:
            return
        self.permissions.add(*extracted)


class ModuleFactory(factory.django.DjangoModelFactory):
    """Factory canônica de módulos exibidos no shell autenticado."""

    class Meta:
        model = Module

    name = factory.Sequence(lambda n: f"Modulo {n}")
    slug = factory.Sequence(lambda n: f"modulo-{n}")
    description = "Modulo de teste"
    icon = "ti ti-layout-grid"
    url_name = "module_entry"
    app_label = ""
    permission_codename = ""
    menu_group = "Teste"
    order = factory.Sequence(lambda n: n)
    is_active = True
    show_in_sidebar = True
    show_in_dashboard = True


class AuditLogFactory(factory.django.DjangoModelFactory):
    """Factory canônica de eventos da trilha de auditoria."""

    class Meta:
        model = AuditLog
        exclude = ("request_id",)

    request_id = factory.Sequence(lambda n: f"req-{n}")
    actor = None
    actor_identifier = factory.Sequence(lambda n: f"actor-{n}")
    action = AuditLog.ACTION_LOGIN
    content_type = None
    object_id = ""
    object_repr = factory.Sequence(lambda n: f"Evento {n}")
    object_verbose_name = "Evento"
    request_method = "GET"
    path = "/painel/auditoria/"
    ip_address = None
    before = factory.LazyFunction(dict)
    after = factory.LazyFunction(dict)
    changes = factory.LazyFunction(dict)
    metadata = factory.LazyAttribute(lambda log: {"request_id": log.request_id})

    @classmethod
    def _create(
        cls,
        model_class: type[AuditLog],
        *args: object,
        **kwargs: object,
    ) -> AuditLog:
        """Permite sobrescrever `created_at` mesmo com `auto_now_add` ativo."""

        created_at = kwargs.pop("created_at", None)
        audit_log = super()._create(model_class, *args, **kwargs)
        if isinstance(created_at, datetime):
            model_class.objects.filter(pk=audit_log.pk).update(created_at=created_at)
            audit_log.refresh_from_db()
        return audit_log
