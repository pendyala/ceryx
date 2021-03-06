"""
Simple Redis client, implemented the data logic of Ceryx.
"""
from rediscluster import RedisCluster
from ceryx import exceptions, schemas, settings

def _str(subject):
    return subject.decode("utf-8") if type(subject) == bytes else str(bytes)


class RedisClient:
    @staticmethod
    def from_config(path=None):
        """
        Returns a RedisClient, using the default configuration from Ceryx
        settings.
        """
        return RedisClient(
            settings.REDIS_HOST,
            settings.REDIS_PORT,
            settings.REDIS_PASSWORD,
            0,
            settings.REDIS_PREFIX,
            settings.REDIS_TIMEOUT,
        )

    def __init__(self, host, port, password, db, prefix, timeout):
        self.client = RedisCluster(host=host, port=port, decode_responses=True)
        print("Redis HOST ===> ")
        print(host)
        self.prefix = prefix
        
    
    def _prefixed_key(self, key):
        return f"{self.prefix}:{key}"

    def _route_key(self, source):
        return self._prefixed_key(f"routes:{source}")

    def _settings_key(self, source):
        return self._prefixed_key(f"settings:{source}")

    def _delete_target(self, host):
        key = self._route_key(host)
        self.client.delete(key)
    
    def _delete_settings(self, host):
        key = self._settings_key(host)
        self.client.delete(key)

    def _lookup_target(self, host, raise_exception=False):
        print ("HOST === " + host)
        key = self._route_key(host)
        target = self.client.get(key)
        
        if target is None and raise_exception:
            raise exceptions.NotFound("Route not found.")
        
        return target

    def _lookup_settings(self, host):
        key = self._settings_key(host)
        return self.client.hgetall(key)

    def lookup_hosts(self, pattern="*"):
        lookup_pattern = self._route_key(pattern)
        print ("---> lookup_pattern --->", lookup_pattern)
        left_padding = len(lookup_pattern) - 1
        print ("---> left_padding ---> ", left_padding)
        keys = self.client.keys(lookup_pattern)
        print ("Keys ---->")
        print(keys)
        print(*keys, sep=", ")
        newKeys = []
        for key in range(len(keys)) :
            temp=keys[key]
            newKeys.append(temp[left_padding:])
        #return [_str(key)[left_padding:] for key in keys]
        return newKeys
    
    def _set_target(self, host, target):
        key = self._route_key(host)
        self.client.set(key, target)

    def _set_settings(self, host, settings):
        key = self._settings_key(host)
        self.client.hmset(key, settings)
    
    def _set_route(self, route: schemas.Route):
        redis_data = route.to_redis()
        self._set_target(route.source, redis_data["target"])
        self._set_settings(route.source, redis_data["settings"])
        return route
    
    def get_route(self, host):
        print ("in get_route ....... host ===> ")
        print (host)
        target = self._lookup_target(host, raise_exception=True)
        settings = self._lookup_settings(host)
        route = schemas.Route.from_redis({
            "source": host,
            "target": target,
            "settings": settings
        })
        return route

    def list_routes(self):
        hosts = self.lookup_hosts()
        print ("hosts ===> ")
        print(*hosts, sep = ", ")
        routes = [self.get_route(host) for host in hosts]
        return routes
    
    def create_route(self, data: dict):
        route = schemas.Route.validate(data)
        return self._set_route(route)
    
    def update_route(self, host: str, data: dict):
        data["source"] = host
        route = schemas.Route.validate(data)
        return self._set_route(route)

    def delete_route(self, host: str):
        self._delete_target(host)
        self._delete_settings(host)

