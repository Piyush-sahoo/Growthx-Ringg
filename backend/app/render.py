"""HyperFrames recap video rendering (S11, garnish / off the critical path).

Produces a HyperFrames-style HTML composition — branded HTML/CSS with
``data-composition`` / ``data-start`` / ``data-duration`` attributes — that a
HyperFrames renderer would turn into a ~10s personalized recap MP4. We only
build the HTML input here (see github.com/heygen-com/hyperframes); rendering to
MP4 is best-effort and never shelled out in tests.
"""

from __future__ import annotations

import html as _html


def build_recap_html(variables: dict) -> str:
    """Return a HyperFrames HTML composition for a personalized 10s recap.

    References ``customer_name``, ``accounts_connected``, ``reports_sent``,
    ``plan_fit`` and the upgrade link from ``variables``.
    """
    v = variables or {}

    def esc(key: str, default: str = "") -> str:
        return _html.escape(str(v.get(key, default)))

    customer_name = esc("customer_name", "there")
    accounts_connected = esc("accounts_connected", "0")
    reports_sent = esc("reports_sent", "0")
    plan_fit = esc("plan_fit", "your plan")
    upgrade_link = _html.escape(
        str(v.get("upgrade_link") or v.get("retry_link") or "https://app.reportzen.example/upgrade")
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>ReportZen recap — {customer_name}</title>
<style>
  body {{ margin: 0; font-family: 'Inter', system-ui, sans-serif; background: #0b1020; }}
  .recap {{ width: 1280px; height: 720px; position: relative; overflow: hidden;
    background: linear-gradient(135deg, #1e1b4b 0%, #0b1020 100%); color: #fff; }}
  .scene {{ position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; text-align: center; padding: 64px; }}
  .brand {{ position: absolute; top: 40px; left: 48px; font-weight: 800;
    letter-spacing: 0.04em; color: #a5b4fc; }}
  h1 {{ font-size: 64px; margin: 0 0 16px; }}
  .stat {{ font-size: 96px; font-weight: 800; color: #818cf8; }}
  .label {{ font-size: 28px; opacity: 0.8; }}
  .cta a {{ display: inline-block; margin-top: 24px; padding: 18px 36px;
    background: #6366f1; color: #fff; border-radius: 999px; font-size: 28px;
    text-decoration: none; font-weight: 700; }}
</style>
</head>
<body>
<div class="recap" data-composition="reportzen-recap" data-duration="10">
  <div class="brand">ReportZen</div>

  <div class="scene" data-start="0" data-duration="2.5">
    <h1>Nice work, {customer_name}.</h1>
    <div class="label">Here's your trial recap.</div>
  </div>

  <div class="scene" data-start="2.5" data-duration="2.5">
    <div class="stat">{accounts_connected}</div>
    <div class="label">accounts connected</div>
  </div>

  <div class="scene" data-start="5" data-duration="2.5">
    <div class="stat">{reports_sent}</div>
    <div class="label">reports sent</div>
  </div>

  <div class="scene cta" data-start="7.5" data-duration="2.5">
    <h1>{plan_fit} fits you.</h1>
    <div class="cta"><a href="{upgrade_link}">Upgrade now</a></div>
  </div>
</div>
</body>
</html>"""


def render_mp4(html: str) -> str | None:
    """Best-effort render of HyperFrames HTML to an MP4 path.

    Returns the output path on success, or ``None`` when node/ffmpeg are
    unavailable. Never shells out during tests — this is intentionally a no-op
    stub that returns ``None`` unless a real renderer is wired up.
    """
    return None
