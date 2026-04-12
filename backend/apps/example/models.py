"""Example models — demonstrate the patterns every app should follow.

Two models with a FK relationship so ``select_related`` has something to do,
plus an ``occurred_at`` + ``amount`` pair so ``TruncMonth`` aggregation has
something to aggregate.
"""
from django.db import models


class ExampleParent(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class ExampleChild(models.Model):
    parent = models.ForeignKey(
        ExampleParent,
        on_delete=models.CASCADE,
        related_name='children',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-occurred_at']

    def __str__(self) -> str:
        return f'{self.parent.name} — {self.amount} @ {self.occurred_at:%Y-%m-%d}'
