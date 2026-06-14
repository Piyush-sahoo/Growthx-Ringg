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


ringg_client = RinggClient()
