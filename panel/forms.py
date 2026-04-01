"""Fachada compatível para os formulários do painel."""

from .groups.forms import PanelGroupForm
from .users.forms import PanelUserForm

__all__ = ["PanelGroupForm", "PanelUserForm"]
