from django.utils.decorators import method_decorator
from functools import wraps
from django.core.cache import cache
from .models import CacheMonitor, CacheSettings
from django.template.response import TemplateResponse


def monitored_cache_page(func=None, *, timeout=None):
    if func is None:
        return lambda func: monitored_cache_page(func, timeout=timeout)

    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if request.method != "GET":
            return func(request, *args, **kwargs)

        path = request.path
        monitor, _ = CacheMonitor.objects.get_or_create(path=path)

        # Check if caching is enabled
        settings = CacheSettings.objects.filter(path=path).first()
        if settings and not settings.is_active:
            monitor.misses += 1
            monitor.save()
            return func(request, *args, **kwargs)

        cache_key = f"view_cache_{path}"
        cached_response = cache.get(cache_key)

        if cached_response is None:
            monitor.misses += 1
            response = func(request, *args, **kwargs)

            # Handle TemplateResponse
            if isinstance(response, TemplateResponse):
                response.render()

            cache_timeout = timeout or (settings.cache_timeout if settings else 900)
            cache.set(cache_key, response, cache_timeout)
            monitor.save()
            return response
        else:
            monitor.hits += 1
            monitor.save()
            return cached_response

    return wrapper
