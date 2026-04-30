from rest_framework.throttling import UserRateThrottle, AnonRateThrottle, SimpleRateThrottle


class BurstRateThrottle(UserRateThrottle):
    scope = 'burst'

    def get_rate(self):
        try:
            return super().get_rate()
        except Exception:
            return None


class SustainedRateThrottle(UserRateThrottle):
    scope = 'sustained'

    def get_rate(self):
        try:
            return super().get_rate()
        except Exception:
            return None


class AnonBurstRateThrottle(AnonRateThrottle):
    scope = 'anon_burst'

    def get_rate(self):
        try:
            return super().get_rate()
        except Exception:
            return None


class IPRateThrottle(SimpleRateThrottle):
    scope = 'ip'

    def get_rate(self):
        try:
            return super().get_rate()
        except Exception:
            return None

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class LoginThrottle(AnonRateThrottle):
    scope = 'login'

    def get_rate(self):
        try:
            return super().get_rate()
        except Exception:
            return None

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {
            'scope': f'{self.scope}_v2',
            'ident': ident,
        }
