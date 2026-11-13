from django.apps import AppConfig


class AgentToolsConfig(AppConfig):
    name = "agent_tools"

    def ready(self):
        # Same registration loop as core (contrib/agent/apps.py:81-96).
        from baserow.contrib.agent.registries import agent_tool_type_registry

        from .tool_types import AGENT_TOOL_TYPES

        for tool_type in AGENT_TOOL_TYPES:
            agent_tool_type_registry.register(tool_type())
