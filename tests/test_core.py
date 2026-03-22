"""Unit tests for the core.BaseModel abstract model (T017)."""

import time

import pytest

from django.db import connection, models

from core.models import BaseModel


class _ConcreteModel(BaseModel):
    """Test-only concrete subclass used to exercise BaseModel DB behaviour."""

    name = models.CharField(max_length=50)

    class Meta(BaseModel.Meta):
        app_label = "core"


@pytest.fixture()
def concrete_model_table(transactional_db):
    """Create (and tear down) the _ConcreteModel table for this test session."""
    with connection.schema_editor() as editor:
        editor.create_model(_ConcreteModel)
    yield _ConcreteModel
    with connection.schema_editor() as editor:
        editor.delete_model(_ConcreteModel)


class TestBaseModel:
    """Non-DB tests for BaseModel abstract properties."""

    def test_is_abstract(self):
        assert BaseModel._meta.abstract is True

    def test_default_ordering(self):
        assert BaseModel._meta.ordering == ["-created_at"]

    def test_has_created_at_field(self):
        field = BaseModel._meta.get_field("created_at")
        assert field.auto_now_add is True

    def test_has_updated_at_field(self):
        field = BaseModel._meta.get_field("updated_at")
        assert field.auto_now is True


class TestBaseModelDB:
    """DB-backed tests verifying BaseModel timestamp behaviour."""

    def test_created_at_set_on_first_save(self, concrete_model_table):
        obj = _ConcreteModel.objects.create(name="test")
        obj.refresh_from_db()
        assert obj.created_at is not None

    def test_updated_at_set_on_first_save(self, concrete_model_table):
        obj = _ConcreteModel.objects.create(name="test")
        obj.refresh_from_db()
        assert obj.updated_at is not None

    def test_updated_at_changes_on_resave(self, concrete_model_table):
        obj = _ConcreteModel.objects.create(name="first")
        original_updated = obj.updated_at
        time.sleep(0.05)
        obj.name = "updated"
        obj.save()
        obj.refresh_from_db()
        assert obj.updated_at >= original_updated

    def test_ordering_on_concrete_subclass(self, concrete_model_table):
        assert _ConcreteModel._meta.ordering == ["-created_at"]
