from baserow.core.ai_provider.constants import AI_PROVIDER_FEATURE_AI_FIELDS
from baserow.core.ai_provider.registries import AIProviderModelFeatureType
from baserow.core.generative_ai.registries import generative_ai_model_type_registry

from .models import AI_PROMPT_FIELD_MODELS


class AIPromptFieldsFeatureType(AIProviderModelFeatureType):
    """Lets admins enable provider models for AI prompt fields."""

    type = AI_PROVIDER_FEATURE_AI_FIELDS

    def count_model_references(self, provider_type, model_identifier, workspace=None):
        count = 0
        for model in AI_PROMPT_FIELD_MODELS:
            queryset = model.objects.filter(
                ai_generative_ai_type=provider_type,
                ai_generative_ai_model=model_identifier,
                table__trashed=False,
                table__database__trashed=False,
                table__database__workspace__trashed=False,
            )
            if workspace is not None:
                queryset = queryset.filter(table__database__workspace=workspace)
            count += queryset.count()
        return count

    def get_workspace_availability(self, workspace, state=None) -> dict:
        models = generative_ai_model_type_registry.get_enabled_models_per_type(
            workspace, feature_type=self.type, state=state
        )
        return {"is_enabled": bool(models), "models": models}
