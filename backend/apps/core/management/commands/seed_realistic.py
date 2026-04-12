"""Realistic seed data command — stub.

Each app spawned from this template should replace this stub with a command
that generates enough realistic data to make local dev feel like production.

Usage (after you fill in the body):

    python manage.py seed_realistic --email you@example.com --clear

Running-balance pattern (required for any money-ish model)
-----------------------------------------------------------
When seeding transactions with a ``balance`` field, do NOT compute the balance
per-row as you insert. Walk the transactions in date order once and carry a
running total per account:

    running = {account.id: Decimal(0) for account in accounts}
    for txn in Transaction.objects.filter(user=user).order_by('occurred_at'):
        running[txn.account_id] += txn.amount
        txn.balance = running[txn.account_id]
        txn.save(update_fields=['balance'])

Rules of thumb:

- Order by ``occurred_at`` ASCENDING so the running total is correct.
- Carry one running value per account (use a dict keyed by account_id).
- ALWAYS set ``last_synced_at = timezone.now()`` on account rows after seeding
  — otherwise a null default leaves the UI displaying "56 years ago" for the
  dev user and every Playwright screenshot looks broken.
- Use ``random.seed(42)`` (or similar) for deterministic output so snapshots
  + screenshot diffs stay stable across runs.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Stub: replace with a command that seeds realistic data for local dev. '
        'See the module docstring for the running-balance pattern.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--auth0_id', type=str, default='')
        parser.add_argument('--email', type=str, default='dev@example.com')
        parser.add_argument('--clear', action='store_true')

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            'seed_realistic is a stub. See apps/core/management/commands/'
            'seed_realistic.py for the running-balance pattern you need to '
            'implement.'
        ))
