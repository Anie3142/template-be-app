"""Performance + caching middleware.

Two pieces:

1. ``CacheControlMiddleware`` — emits ``Cache-Control: private, max-age=...`` on
   GET responses for read-mostly endpoints. The browser keeps a copy and skips
   the network entirely for repeated visits within the TTL. ``private`` means
   shared caches (CDNs, ISPs) won't store it — only the user's browser.

2. ``ServerTimingMiddleware`` — emits a ``Server-Timing`` header with database
   time, view time, and total wall-clock time. Visible in Chrome/Firefox DevTools
   under Network → Headers → Timing. Lets us measure perf without guessing.

Both are intentionally tiny and have zero impact on responses they don't touch.
"""
from __future__ import annotations

import time

from django.db import connection
from django.utils.deprecation import MiddlewareMixin


# Endpoints whose data changes rarely (minutes, not seconds). Cached in the
# user's browser so a back-button or page reload paints from disk instead of
# hitting Django. Path is matched as a startswith — query strings still vary
# the cache key naturally because they're part of the URL.
#
# Add your read-mostly paths here when you build them.
CACHEABLE_PATHS: tuple[str, ...] = (
    '/api/v1/example/monthly-totals',
)

CACHE_MAX_AGE_SECONDS = 300  # 5 minutes


class CacheControlMiddleware(MiddlewareMixin):
    """Tag GET responses on read-mostly endpoints with a private browser cache."""

    def process_response(self, request, response):
        if request.method != 'GET':
            return response
        if response.status_code != 200:
            return response
        path = request.path
        for prefix in CACHEABLE_PATHS:
            if path == prefix or path.startswith(prefix + '/') or path.startswith(prefix + '?'):
                response['Cache-Control'] = f'private, max-age={CACHE_MAX_AGE_SECONDS}'
                # Vary on Authorization so a logged-out request doesn't share a
                # cache entry with a logged-in one.
                response['Vary'] = 'Authorization'
                break
        return response


class ServerTimingMiddleware(MiddlewareMixin):
    """Emit a Server-Timing header with db / view / total wall-clock breakdown.

    Lets us see in DevTools whether a slow request is the database, the
    serializer, or something else — without adding logging or guessing.
    """

    def process_request(self, request):
        request._perf_start = time.perf_counter()
        # connection.queries_log is a deque of recently executed queries when
        # DEBUG=True. Snapshot the count so we can diff at response time.
        request._perf_db_queries_start = len(connection.queries)

    def process_response(self, request, response):
        start = getattr(request, '_perf_start', None)
        if start is None:
            return response
        total_ms = (time.perf_counter() - start) * 1000

        # Sum query durations from the snapshot window. queries_log only fills
        # when DEBUG=True; in production we just report total + query count.
        db_count_start = getattr(request, '_perf_db_queries_start', 0)
        recent_queries = connection.queries[db_count_start:]
        db_ms = sum(float(q.get('time', 0)) for q in recent_queries) * 1000
        db_count = len(recent_queries)
        view_ms = max(total_ms - db_ms, 0)

        parts = [
            f'total;dur={total_ms:.1f}',
            f'db;dur={db_ms:.1f};desc="{db_count} queries"',
            f'view;dur={view_ms:.1f}',
        ]
        response['Server-Timing'] = ', '.join(parts)
        return response
