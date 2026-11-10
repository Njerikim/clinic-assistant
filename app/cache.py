from collections import OrderedDict


class TenantCache:
    """Small LRU. The tenant and index version are part of the key, so entries never cross tenants."""

    def __init__(self, size: int = 256) -> None:
        self._size = size
        self._data: OrderedDict = OrderedDict()

    @staticmethod
    def _key(tenant: str, version: str, question: str):
        return (tenant, version, " ".join(question.lower().split()))

    def get(self, tenant, version, question):
        key = self._key(tenant, version, question)
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None

    def set(self, tenant, version, question, value) -> None:
        key = self._key(tenant, version, question)
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self._size:
            self._data.popitem(last=False)
