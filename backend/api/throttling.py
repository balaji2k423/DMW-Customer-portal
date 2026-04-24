from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'

class SustainedRateThrottle(UserRateThrottle):
    scope = 'sustained'

class AnonBurstRateThrottle(AnonRateThrottle):
    scope = 'anon_burst'

class IPRateThrottle(UserRateThrottle):
    """Rate limit per IP address regardless of auth status."""
    scope = 'ip'

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)  # gets real IP
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }