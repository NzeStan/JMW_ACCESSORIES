from functools import wraps
from django.core.cache import cache
from rest_framework.response import Response

def cache_api_response(timeout=900, key_prefix='api'):
    """Cache DRF API responses"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Build cache key
            cache_key = f"{key_prefix}:{request.path}:{request.query_params}"
            
            # Try cache
            cached_data = cache.get(cache_key)
            if cached_data:
                return Response(cached_data)
            
            # Get fresh response
            response = view_func(self, request, *args, **kwargs)
            
            # Cache successful responses
            if response.status_code == 200:
                cache.set(cache_key, response.data, timeout)
            
            return response
        return wrapper
    return decorator