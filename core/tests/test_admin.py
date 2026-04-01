"""Testes do admin customizado do app core."""

from django.contrib.auth import get_user_model
from django.test import TestCase
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
