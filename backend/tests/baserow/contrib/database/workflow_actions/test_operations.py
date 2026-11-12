from baserow.contrib.database.workflow_actions.operations import (
    DispatchDatabaseWorkflowActionOperationType,
)
from baserow.core.registries import operation_type_registry


def test_the_dispatch_operation_is_registered():
    operation = operation_type_registry.get(
        DispatchDatabaseWorkflowActionOperationType.type
    )

    # The field, since that is all a grid cell has to ask the question with.
    assert operation.context_scope_name == "database_field"

