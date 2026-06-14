"""Thin client for the Ringg AI outbound calling API.

Docs: https://docs.ringg.ai  (skill reference: info/ringg-ai-skill.md)
Base URL: https://prod-api.ringg.ai/ca/api/v0
Auth: X-API-KEY header.
Endpoint used: POST /calling/outbound/individual
"""

import httpx

from .config import get_settings


class RinggError(RuntimeError):
    """Raised when the Ringg API returns an error or is not configured."""


class RinggClient:
    def __init__(self) -> None:
        self._settings = get_settings()

    @property
    def configured(self) -> bool:
        return bool(self._settings.ringg_api_key)

    async def place_outbound_call(
        self,
        *,
        name: str,
        phone_number: str,
        custom_args_values: dict,
        assistant_id: str | None = None,
    ) -> dict:
        """Place a single outbound call and return the Ringg response JSON.

        Contract (docs.ringg.ai initiate-individual-call): body uses `name`,
        `mobile_number` (E.164), `agent_id`, and exactly one caller id
        (`from_number_id` preferred). Returns the Ringg JSON containing the call id.
        """
        if not self.configured:
            raise RinggError(
                "RINGG_API_KEY is not set. Add it to the backend environment."
            )

        assistant = assistant_id or self._settings.ringg_assistant_id
        if not assistant:
            raise RinggError("No assistant id provided (set RINGG_ASSISTANT_ID).")

        url = f"{self._settings.ringg_base_url.rstrip('/')}/calling/outbound/individual"
        payload: dict = {
            "name": name,
            "mobile_number": phone_number,
            "agent_id": assistant,
            "custom_args_values": custom_args_values,
        }
        # Prefer from_number_id over a raw number (never send both).
        if self._settings.ringg_from_number_id:
            payload["from_number_id"] = self._settings.ringg_from_number_id

        headers = {
            "X-API-KEY": self._settings.ringg_api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            raise RinggError(f"Ringg API {resp.status_code}: {resp.text}")
        return resp.json()

    @property
    def _headers(self) -> dict:
        return {"X-API-KEY": self._settings.ringg_api_key, "Content-Type": "application/json"}

    async def get_workspace(self) -> dict:
        """Return workspace info (used for credit checks before runs)."""
        if not self.configured:
            raise RinggError("RINGG_API_KEY is not set.")
        url = f"{self._settings.ringg_base_url.rstrip('/')}/workspace"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers)
        if resp.status_code >= 400:
            raise RinggError(f"Ringg workspace {resp.status_code}: {resp.text}")
        return resp.json()

    async def credits(self) -> float:
        """Available workspace credits."""
        info = (await self.get_workspace()).get("workspace_info", {})
        return float(info.get("total_available_credits") or info.get("credits") or 0)

    async def list_voices(self, language: str) -> list[dict]:
        url = f"{self._settings.ringg_base_url.rstrip('/')}/agent/voices"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers, params={"language": language})
        if resp.status_code >= 400:
            raise RinggError(f"Ringg voices {resp.status_code}: {resp.text}")
        return resp.json().get("voices", [])

    async def resolve_voice_id(self, language: str) -> str:
        if self._settings.agent_voice_id:
            return self._settings.agent_voice_id
        voices = await self.list_voices(language)
        if not voices:
            raise RinggError(f"No Ringg voices available for language {language}")
        return voices[0]["id"]

    async def create_agent(self, payload: dict) -> str:
        """Create a Ringg assistant (POST /public/agent/). Returns the agent_id.

        Note the trailing slash — without it the API issues a 307 that drops the body.
        """
        if not self.configured:
            raise RinggError("RINGG_API_KEY is not set.")
        url = f"{self._settings.ringg_base_url.rstrip('/')}/public/agent/"
        async with httpx.AsyncClient(timeout=40) as client:
            resp = await client.post(url, json=payload, headers=self._headers)
        if resp.status_code >= 400:
            raise RinggError(f"Ringg create-agent {resp.status_code}: {resp.text}")
        data = resp.json()
        agent_id = (
            (data.get("data") or {}).get("agent_id")
            if isinstance(data.get("data"), dict)
            else None
        ) or data.get("agent_id")
        if not agent_id:
            raise RinggError(f"Ringg create-agent returned no agent_id: {data}")
        return agent_id

    async def subscribe_webhooks(
        self,
        *,
        agent_id: str,
        callback_url: str,
        event_types: list[str],
        secret: str = "",
    ) -> dict:
        """Subscribe an assistant's webhooks to our callback (PATCH /agent/v1)."""
        if not self.configured:
            raise RinggError("RINGG_API_KEY is not set.")
        headers = {"Content-Type": "application/json"}
        if secret:
            headers["X-Webhook-Secret"] = secret
        body = {
            "operation": "edit_event_subscriptions",
            "agent_id": agent_id,
            "event_subscriptions": [
                {
                    "event_type": event_types,
                    "callback_url": callback_url,
                    "headers": headers,
                    "method_type": "POST",
                }
            ],
        }
        url = f"{self._settings.ringg_base_url.rstrip('/')}/agent/v1"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.patch(url, json=body, headers=self._headers)
        if resp.status_code >= 400:
            raise RinggError(f"Ringg subscribe {resp.status_code}: {resp.text}")
        return resp.json()


ringg_client = RinggClient()
