"""Endpoints JSON protegidos do domínio de usuários do painel."""

from __future__ import annotations

import json
from json import JSONDecodeError

from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.api_auth import api_error_response, require_api_permission

from .api_forms import ApiUserWriteForm


def _parse_json_body(request: HttpRequest) -> tuple[dict, JsonResponse | None]:
    """Converte o corpo JSON da requisição em dicionário Python."""

    if not request.body:
        return {}, None

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, JSONDecodeError):
        return {}, api_error_response(
            "O corpo da requisição deve ser um JSON válido.",
            code="invalid_json",
            status=400,
        )

    if not isinstance(payload, dict):
        return {}, api_error_response(
            "O corpo JSON deve ser um objeto com pares chave/valor.",
            code="invalid_payload",
            status=400,
        )

    return payload, None


def _serialize_user(user: User) -> dict[str, object]:
    """Resume o usuário em um payload legível para os consumidores da API."""

    return {
        "id": user.pk,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "is_active": user.is_active,
        "groups": [
            {"id": group.pk, "name": group.name}
            for group in user.groups.order_by("name")
        ],
    }


def _json_form_errors(form: ApiUserWriteForm) -> JsonResponse:
    """Retorna erros de validação do formulário em formato JSON padronizado."""

    return JsonResponse(
        {
            "detail": "Os dados enviados são inválidos.",
            "code": "validation_error",
            "errors": form.errors.get_json_data(),
        },
        status=400,
    )


def _build_user_form_data(payload: dict, *, instance: User | None = None) -> dict[str, object]:
    """Normaliza o payload da API em dados compatíveis com o formulário."""

    existing_groups = []
    if instance is not None:
        existing_groups = list(instance.groups.values_list("pk", flat=True))

    return {
        "username": payload.get("username", instance.username if instance else ""),
        "first_name": payload.get("first_name", instance.first_name if instance else ""),
        "last_name": payload.get("last_name", instance.last_name if instance else ""),
        "email": payload.get("email", instance.email if instance else ""),
        "is_active": payload.get("is_active", instance.is_active if instance else True),
        "groups": payload.get("groups", existing_groups),
        "password": payload.get("password", ""),
    }


@csrf_exempt
@require_api_permission("panel.users")
def users_collection(request: HttpRequest) -> HttpResponse:
    """Lista e cria usuários comuns via token Bearer da API."""

    if request.method == "GET":
        users = (
            User.objects.filter(is_superuser=False)
            .prefetch_related("groups")
            .order_by("username")
        )
        return JsonResponse(
            {
                "count": users.count(),
                "results": [_serialize_user(user) for user in users],
            }
        )

    if request.method == "POST":
        payload, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        form = ApiUserWriteForm(
            data=_build_user_form_data(payload),
            require_password=True,
        )
        if not form.is_valid():
            return _json_form_errors(form)

        user = form.save()
        return JsonResponse(_serialize_user(user), status=201)

    return api_error_response(
        "Método não permitido para este endpoint.",
        code="method_not_allowed",
        status=405,
    )


@csrf_exempt
@require_api_permission("panel.users")
def user_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """Consulta, altera ou remove um usuário comum pela API."""

    user = User.objects.filter(pk=pk, is_superuser=False).prefetch_related("groups").first()
    if user is None:
        return api_error_response(
            "Usuário não encontrado.",
            code="not_found",
            status=404,
        )

    if request.method == "GET":
        return JsonResponse(_serialize_user(user))

    if request.method in {"PUT", "PATCH"}:
        payload, error_response = _parse_json_body(request)
        if error_response:
            return error_response

        form = ApiUserWriteForm(
            data=_build_user_form_data(payload, instance=user),
            instance=user,
        )
        if not form.is_valid():
            return _json_form_errors(form)

        updated_user = form.save()
        return JsonResponse(_serialize_user(updated_user))

    if request.method == "DELETE":
        user.delete()
        return HttpResponse(status=204)

    return api_error_response(
        "Método não permitido para este endpoint.",
        code="method_not_allowed",
        status=405,
    )
