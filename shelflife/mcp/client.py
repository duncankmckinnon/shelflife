from httpx import AsyncClient, Response


class ShelflifeClient:
    """Thin wrapper around httpx.AsyncClient that translates HTTP responses
    into dicts suitable for MCP tool returns."""

    def __init__(self, http: AsyncClient) -> None:
        self.http = http

    async def get(self, path: str, **kwargs) -> dict | list:
        resp = await self.http.get(path, **kwargs)
        return self._handle(resp)

    async def post(self, path: str, **kwargs) -> dict | list:
        resp = await self.http.post(path, **kwargs)
        return self._handle(resp)

    async def put(self, path: str, **kwargs) -> dict | list:
        resp = await self.http.put(path, **kwargs)
        return self._handle(resp)

    async def delete(self, path: str, **kwargs) -> dict | list:
        resp = await self.http.delete(path, **kwargs)
        return self._handle(resp)

    async def upload(self, path: str, files: dict, **kwargs) -> dict | list:
        resp = await self.http.post(path, files=files, **kwargs)
        return self._handle(resp)

    def _handle(self, resp: Response) -> dict | list:
        if resp.status_code == 204:
            return {"ok": True}
        if resp.status_code >= 500:
            raise RuntimeError(f"Server error {resp.status_code}: {resp.text}")
        if resp.status_code >= 400:
            detail = resp.json().get("detail", resp.text)
            return {"error": True, "status": resp.status_code, "detail": detail}
        return resp.json()
