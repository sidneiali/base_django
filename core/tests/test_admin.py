"""Testes do admin customizado do app core."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


class UserAdminTests(TestCase):
    """Garante compatibilidade do admin customizado com o Django 6."""

    def test_admin_user_add_view_loads(self):
        """A tela de criação de usuário no admin precisa abrir sem FieldError."""

        admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="senha-forte",
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:auth_user_add"))

        self.assertEqual(response.status_code, 200)

    @override_settings(ENABLE_DJANGO_ADMIN=False)
    def test_admin_routes_return_404_when_admin_is_disabled(self):
        """A flag de configuração deve derrubar toda a superfície do admin."""

        root_response = self.client.get("/admin/")
        login_response = self.client.get("/admin/login/")

        self.assertEqual(root_response.status_code, 404)
        self.assertEqual(login_response.status_code, 404)
