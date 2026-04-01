"""Fachada compatível para os formulários do painel."""

from .groups.forms import PanelGroupForm
from .modules.forms import PanelModuleForm
from .users.forms import PanelUserForm

__all__ = ["PanelGroupForm", "PanelModuleForm", "PanelUserForm"]
