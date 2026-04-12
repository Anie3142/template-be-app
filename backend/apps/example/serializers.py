"""Example serializers — one per model."""
from rest_framework import serializers

from .models import ExampleChild, ExampleParent


class ExampleParentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExampleParent
        fields = ['id', 'name', 'created_at']


class ExampleChildSerializer(serializers.ModelSerializer):
    # Nested read-only parent. Without select_related in the view this forces
    # one extra query per row — the N+1 trap. The view below calls
    # select_related('parent') to collapse that into a single JOIN.
    parent_name = serializers.CharField(source='parent.name', read_only=True)

    class Meta:
        model = ExampleChild
        fields = ['id', 'parent', 'parent_name', 'amount', 'occurred_at', 'created_at']
