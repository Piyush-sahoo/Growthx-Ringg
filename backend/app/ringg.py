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

    async def call_history(
        self, *, page: int = 1, page_size: int = 25, agent_id: str | None = None
    ) -> dict:
        """Fetch real call history from Ringg, normalized for the UI."""
        from .models import transcript_to_text

        url = f"{self._settings.ringg_base_url.rstrip('/')}/calling/history"
        params = {"page": page, "page_size": page_size}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers, params=params)
        if resp.status_code >= 400:
            raise RinggError(f"Ringg history {resp.status_code}: {resp.text}")
        data = resp.json()
        calls = data.get("calls", []) if isinstance(data, dict) else []
        out = []
        for c in calls:
            agent = c.get("agent") or {}
            if agent_id and agent.get("id") != agent_id:
                continue
            out.append(
                {
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "to_number": c.get("to_number"),
                    "status": c.get("status"),
                    "agent_id": agent.get("id"),
                    "agent_name": agent.get("agent_name"),
                    "duration": c.get("call_duration"),
                    "cost": c.get("call_cost"),
                    "currency": c.get("currency"),
                    "created_at": c.get("created_at"),
                    "transcript": transcript_to_text(c.get("transcript")),
                    "recording_url": c.get("audio_recording"),
                }
            )
        return {"calls": out, "total": data.get("total"), "count": data.get("count")}

    async def list_agents(self) -> list[dict]:
        """Return callable agents: [{id, name, type}]."""
        url = f"{self._settings.ringg_base_url.rstrip('/')}/agent/all"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers)
        if resp.status_code >= 400:
            raise RinggError(f"Ringg agents {resp.status_code}: {resp.text}")
        agents = resp.json().get("data", {}).get("agents", [])
        return [
            {
                "id": a.get("id"),
                "name": a.get("agent_display_name") or a.get("agent_name") or a.get("id"),
                "type": a.get("agent_type"),
            }
            for a in agents
            if a.get("id")
        ]

    async def get_agent_variables(self, agent_id: str) -> list[str]:
        """Return an agent's custom_variables (from its latest version config)."""
        url = f"{self._settings.ringg_base_url.rstrip('/')}/agent/{agent_id}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers)
        if resp.status_code >= 400:
            raise RinggError(f"Ringg agent {resp.status_code}: {resp.text}")
        data = resp.json()
        agents = data.get("agents") or data.get("data", {}).get("agents")
        version_details = None
        if isinstance(agents, dict):
            version_details = agents.get("version_details")
        elif isinstance(agents, list) and agents:
            version_details = agents[0].get("version_details")
        if isinstance(version_details, dict):
            for ver in version_details.values():
                cv = (ver.get("agent_config") or {}).get("custom_variables")
                if cv:
                    return list(cv)
        return []

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
