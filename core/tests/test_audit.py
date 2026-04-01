"""Testes da trilha de auditoria do app core."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from core.models import AuditLog, Module

User = get_user_model()


class AuditLogTests(TestCase):
    """Valida os sinais e eventos da trilha de auditoria."""

    def _build_module(self) -> Module:
        """Cria um modulo valido para os testes de CRUD."""

        return Module.objects.create(
            name="Usuários",
            slug="usuarios",
            description="Gestão de usuários",
            icon="ti ti-users",
            url_name="panel_users_list",
            app_label="auth",
            permission_codename="view_user",
            menu_group="Configurações",
            order=10,
            is_active=True,
        )

    def test_module_crud_generates_audit_logs(self):
        """Cria, altera e exclui modulo gerando eventos distintos."""

        module = self._build_module()
        module_id = str(module.pk)

        create_log = AuditLog.objects.get(
            action=AuditLog.ACTION_CREATE,
            object_id=module_id,
        )
        self.assertEqual(create_log.object_repr, module.name)

        module.description = "Gestão central de usuários"
        module.save()

        update_log = AuditLog.objects.filter(
            action=AuditLog.ACTION_UPDATE,
            object_id=module_id,
        ).first()
        self.assertIsNotNone(update_log)
        self.assertIn("description", update_log.changes)

        module.delete()

        delete_log = AuditLog.objects.filter(
            action=AuditLog.ACTION_DELETE,
            object_id=module_id,
        ).first()
        self.assertIsNotNone(delete_log)
        self.assertEqual(delete_log.before["name"], "Usuários")

    def test_group_membership_changes_are_logged(self):
        """Registra alteracoes de grupos em usuarios como update."""

        user = User.objects.create_user(username="maria", password="senha-forte")
        group = Group.objects.create(name="Equipe")
        AuditLog.objects.all().delete()

        user.groups.add(group)

        log = AuditLog.objects.get(action=AuditLog.ACTION_UPDATE)
        self.assertEqual(log.object_id, str(user.pk))
        self.assertEqual(log.changes["groups"]["operation"], "post_add")
        self.assertEqual(
            log.changes["groups"]["changed_items"],
            [{"id": str(group.pk), "repr": group.name}],
        )

    def test_authentication_events_are_logged(self):
        """Loga login, logout e falha de login no banco de auditoria."""

        user = User.objects.create_user(username="ana", password="senha-forte")
        AuditLog.objects.all().delete()

        login_response = self.client.post(
            reverse("login"),
            {"username": "ana", "password": "senha-forte"},
        )
        self.assertEqual(login_response.status_code, 302)

        logout_response = self.client.post(reverse("logout"))
        self.assertEqual(logout_response.status_code, 302)

        failed_login_response = self.client.post(
            reverse("login"),
            {"username": "ana", "password": "senha-incorreta"},
        )
        self.assertEqual(failed_login_response.status_code, 200)

        actions = list(
            AuditLog.objects.order_by("created_at", "id").values_list("action", flat=True)
        )
        self.assertIn(AuditLog.ACTION_LOGIN, actions)
        self.assertIn(AuditLog.ACTION_LOGOUT, actions)
        self.assertIn(AuditLog.ACTION_LOGIN_FAILED, actions)

        failed_log = AuditLog.objects.filter(
            action=AuditLog.ACTION_LOGIN_FAILED
        ).first()
        self.assertIsNotNone(failed_log)
        self.assertEqual(failed_log.actor_identifier, user.username)
