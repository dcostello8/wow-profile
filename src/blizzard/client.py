import time
from dataclasses import dataclass

import requests


DEFAULT_TIMEOUT = 30
NAMESPACE_PROFILE = "profile"
NAMESPACE_STATIC = "static"
DYNAMIC_NAMESPACE_TYPES = {
    "dynamic",
    "dynamic-classic",
    "dynamic-classic1x",
}


@dataclass(frozen=True)
class BlizzardRequest:
    path: str
    namespace_type: str
    params: dict | None = None


def region_hosts(region):
    if region == "cn":
        raise RuntimeError("The China Battle.net region is not supported by this utility.")
    return {
        "oauth": f"https://{region}.battle.net/oauth",
        "api": f"https://{region}.api.blizzard.com",
    }


def namespace(namespace_type, region):
    return f"{namespace_type}-{region}"


class BlizzardClient:
    def __init__(
        self,
        config,
        access_token,
        hosts=None,
        session=None,
        timeout=DEFAULT_TIMEOUT,
    ):
        self.config = config
        self.region = config["region"]
        self.locale = config["locale"]
        self.hosts = hosts or region_hosts(self.region)
        self.access_token = access_token
        self.session = session or requests.Session()
        self.timeout = timeout

    def get(self, path, namespace_type=NAMESPACE_PROFILE, params=None):
        request = BlizzardRequest(
            path=path,
            namespace_type=namespace_type,
            params=params or {},
        )
        return self.request(request)

    def request(self, request):
        params = {
            "namespace": namespace(request.namespace_type, self.region),
            "locale": self.locale,
            **(request.params or {}),
        }
        response = self.session.get(
            self.url(request.path),
            headers={"Authorization": f"Bearer {self.access_token}"},
            params=params,
            timeout=self.timeout,
        )
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                time.sleep(min(int(retry_after), 2))
                response = self.session.get(
                    self.url(request.path),
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    params=params,
                    timeout=self.timeout,
                )
        response.raise_for_status()
        return response.json()

    def url(self, path):
        clean_path = "/" + str(path).lstrip("/")
        return f"{self.hosts['api']}{clean_path}"

