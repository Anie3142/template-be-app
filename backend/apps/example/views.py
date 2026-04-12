"""Example views — canonical patterns every new app should copy.

Baked-in patterns:

- ``select_related('parent')`` to avoid the N+1 trap when serializing the
  nested parent name (see ``ExampleChildSerializer.parent_name``).
- ``TruncMonth`` + ``Sum`` aggregation in a single query for a monthly report
  — never loop over months firing individual queries.
- ``DevExemptUserRateThrottle`` applied explicitly so tests don't hit limits.
"""
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce, TruncMonth
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.throttling import DevExemptUserRateThrottle

from .models import ExampleChild, ExampleParent
from .serializers import ExampleChildSerializer, ExampleParentSerializer


class ExampleParentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExampleParent.objects.all()
    serializer_class = ExampleParentSerializer
    throttle_classes = [DevExemptUserRateThrottle]


class ExampleChildViewSet(viewsets.ReadOnlyModelViewSet):
    """CRUD on ExampleChild plus a ``monthly_totals`` report action."""

    serializer_class = ExampleChildSerializer
    throttle_classes = [DevExemptUserRateThrottle]

    def get_queryset(self):
        # select_related pulls parent in the same JOIN — without it, each row
        # fires an extra SELECT when the serializer reads parent.name.
        return ExampleChild.objects.select_related('parent').all()

    @action(detail=False, methods=['get'], url_path='monthly-totals')
    def monthly_totals(self, request):
        """Monthly sum aggregation — single query, no Python loop over months.

        TruncMonth buckets rows by calendar month on the DB side. Coalesce is
        defensive against empty months.
        """
        rows = (
            ExampleChild.objects
            .annotate(month=TruncMonth('occurred_at'))
            .values('month')
            .annotate(total=Coalesce(Sum('amount'), Decimal('0')))
            .order_by('month')
        )
        return Response(list(rows))
