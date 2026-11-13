from django.apps import AppConfig


class AITablesConfig(AppConfig):
    name = "ai_tables"

    def ready(self):
        from baserow.contrib.database.fields.registries import field_type_registry
        from baserow.core.ai_provider.registries import (
            ai_provider_model_feature_type_registry,
        )
        from baserow.core.jobs.registries import job_type_registry
        from baserow.core.registries import plugin_registry

        from .ai_provider_feature_types import AIPromptFieldsFeatureType
        from .field_types import AI_PROMPT_FIELD_TYPES
        from .job_types import GenerateAIPromptValuesJobType, TransformAICellsJobType
        from .plugins import AITablesPlugin

        for field_type in AI_PROMPT_FIELD_TYPES:
            field_type_registry.register(field_type())
        job_type_registry.register(GenerateAIPromptValuesJobType())
        job_type_registry.register(TransformAICellsJobType())
        ai_provider_model_feature_type_registry.register(AIPromptFieldsFeatureType())
        plugin_registry.register(AITablesPlugin())
