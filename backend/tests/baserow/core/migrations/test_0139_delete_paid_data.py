from importlib import import_module
from unittest.mock import Mock

delete_paid_data = import_module(
    "baserow.core.migrations.0139_delete_paid_data"
).delete_paid_data


def test_0139_delete_paid_data_is_noop_without_oss_only(settings):
    settings.BASEROW_OSS_ONLY = False
    apps, schema_editor = Mock(), Mock()

    delete_paid_data(apps, schema_editor)

    apps.get_model.assert_not_called()
    apps.get_models.assert_not_called()
    schema_editor.connection.cursor.assert_not_called()
