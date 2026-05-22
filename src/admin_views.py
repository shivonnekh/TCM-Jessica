"""Admin HTML views — agent config inspector + per-turn trace viewer.

Exposed at:
  GET /admin                   → list every agent (prompt / model / tools)
  GET /admin/traces            → recent turn list
  GET /admin/traces/{turn_id}  → per-turn drill-down

Pure read-only. No mutations from this surface.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

HKT = timezone(timedelta(hours=8))


def _to_hkt(iso_utc: str) -> str:
    """Convert a UTC ISO timestamp string to 'YYYY-MM-DD HH:MM:SS HKT'."""
    if not iso_utc:
        return ""
    s = iso_utc.replace("Z", "")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return iso_utc[:19].replace("T", " ")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    hkt = dt.astimezone(HKT)
    return hkt.strftime("%Y-%m-%d %H:%M:%S")

from src.agents import (
    appointment_agent,
    casual_agent,
    constitution_agent,
    faq_agent,
    greeting_agent,
    planner,
    sales_agent,
    writer,
)
from src.agents.base import SPECIALIST_CATALOG, render_specialist_menu_zh
from src.crm.models import Constitution
from src.tools import prompt_overrides
from src.tools.acupoint_images import AcupointImageMap
from src.tools.kb_index import KBIndex
from src.tools.pitch_playbook import PitchPlaybook
from src.tools.product_catalog import ProductCatalog
from src.tools.promotions import PromotionsLoader
from src.tools.recipe_extractor import RecipeExtractor
from src.trace.writer import TraceWriter

router = APIRouter(tags=["admin"])


# -------------------------------------------------------------------
# Shared styling
# -------------------------------------------------------------------


_BASE_CSS = """
:root {
  --bg: #fafaf7; --card: #fff; --ink: #1a1a1a; --muted: #6b6b6b;
  --line: #e3e3df; --accent: #2d6a4f; --accent-soft: #d8f3dc;
  --warn: #c44d3a; --code-bg: #f4f1ed;
  --planner: #d8f3dc; --writer: #fce4dc;
  --tool: #e3f2fd; --kb: #f3e5f5;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--bg); color: var(--ink); line-height: 1.5;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
    "PingFang HK", "PingFang SC", "Microsoft YaHei", sans-serif;
}
.wrap { max-width: 1200px; margin: 0 auto; padding: 1.5rem 1.2rem 4rem; }
nav { background: var(--accent); color: white; padding: 0.75rem 1.2rem; display:flex; gap:1.2rem; align-items:center; }
nav a { color: rgba(255,255,255,0.85); text-decoration: none; font-size: 0.95rem; }
nav a:hover, nav a.active { color: white; font-weight: 600; }
nav .spacer { flex: 1; }
nav .label { font-size: 0.85rem; opacity: 0.7; }
h1 { font-size: 1.5rem; margin: 0 0 0.4rem; }
h2 { font-size: 1.15rem; margin: 1.8rem 0 0.8rem; padding-bottom: 0.3rem; border-bottom: 1px solid var(--line); }
h3 { font-size: 0.95rem; margin: 1rem 0 0.4rem; color: var(--accent); }
.sub { color: var(--muted); font-size: 0.9rem; margin-bottom: 1rem; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 1rem 1.15rem; margin: 0.6rem 0; }
pre { background: var(--code-bg); padding: 0.9rem 1rem; border-radius: 6px; overflow-x: auto; font-size: 0.82rem; line-height: 1.5; white-space: pre-wrap; word-break: break-word; }
code { background: var(--code-bg); padding: 0.05rem 0.35rem; border-radius: 3px; font-size: 0.85em; }
details { background: var(--card); border: 1px solid var(--line); border-radius: 8px; margin: 0.5rem 0; }
details > summary { padding: 0.6rem 0.9rem; cursor: pointer; user-select: none; font-weight: 500; font-size: 0.95rem; }
details[open] > summary { border-bottom: 1px solid var(--line); }
details > .body { padding: 0.5rem 1rem 1rem; }
.tag { display:inline-block; padding:0.1rem 0.5rem; border-radius:4px; font-size:0.75rem; margin-right:0.3rem; }
.tag.tool { background: var(--tool); color:#1e40af; }
.tag.kb { background: var(--kb); color:#6b21a8; }
.tag.muted { background: var(--code-bg); color: var(--muted); }
.tag.green { background: var(--accent-soft); color: var(--accent); }
.tag.red { background: #fce4dc; color: var(--warn); }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; margin: 0.5rem 0; }
th, td { padding: 0.5rem 0.7rem; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
th { background: var(--code-bg); font-weight: 600; }
.kv { display: grid; grid-template-columns: 180px 1fr; gap: 0.3rem 0.8rem; font-size: 0.88rem; }
.kv .k { color: var(--muted); }
.bubble { background: var(--accent-soft); padding: 0.5rem 0.8rem; border-radius: 10px; margin: 0.25rem 0; max-width: 90%; display: inline-block; font-size: 0.9rem; }
.bubble.user { background: #cfe9ff; }
.section { margin: 1.2rem 0; }
.section .head { font-weight: 600; margin-bottom: 0.4rem; }
.pill { display:inline-block; background: var(--planner); color: var(--accent); padding:0.15rem 0.55rem; border-radius:999px; font-size:0.72rem; margin-left:0.3rem; }
.pill.writer { background: var(--writer); color: var(--warn); }
.pill.gray { background: var(--code-bg); color: var(--muted); }
.scroll { max-height: 480px; overflow-y: auto; }
"""


def _nav(active: str) -> str:
    """Top nav bar. `active` is the current page key."""

    def link(href: str, label: str, key: str) -> str:
        cls = "active" if active == key else ""
        return f'<a href="{href}" class="{cls}">{label}</a>'

    return f"""<nav>
  <span class="label">Jessica Admin</span>
  {link("/dev/", "💬 Chat", "chat")}
  {link("/admin", "⚙️ Agents", "agents")}
  {link("/admin/traces", "📊 Traces", "traces")}
  <span class="spacer"></span>
  <span class="label">{html.escape(active.title())}</span>
</nav>"""


def _wrap_page(title: str, active: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-HK"><head><meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{_BASE_CSS}</style>
</head><body>{_nav(active)}<div class="wrap">{body}</div></body></html>"""


# -------------------------------------------------------------------
# /admin — agent config inspector
# -------------------------------------------------------------------


# Source-of-truth for what each agent uses. Lives here so we don't have
# to import + scan every tool; cheaper to maintain manually.
_AGENT_META: list[dict[str, Any]] = [
    {
        "name": "Planner",
        "key": "planner",
        "module": planner,
        "model_attr": "DEFAULT_MODEL",
        "file": "src/agents/planner.py",
        "purpose": "决定 1-2 个 specialist 处理本回合，rule fast-path + LLM fallback",
        "tools": ["rule fast-paths (no external)"],
        "kb": [],
        "prompt_renderer": "planner._build_system_prompt",
        "max_tokens_attr": None,
    },
    {
        "name": "Greeting Agent",
        "key": "greeting",
        "override_key": "greeting_system",
        "module": greeting_agent,
        "model_attr": "DEFAULT_MODEL",
        "file": "src/agents/greeting_agent.py",
        "purpose": "First-touch onboarding only — 官方 intro (verbatim from data/greetings.json + 醫師相)",
        "tools": ["data/greetings.json (官方 intro 模板)"],
        "kb": [],
        "prompt_attr": "_SYSTEM",
        "max_tokens_attr": None,
    },
    {
        "name": "Casual Talk Agent",
        "key": "casual",
        "override_key": "casual_system",
        "module": casual_agent,
        "model_attr": "DEFAULT_MODEL",
        "file": "src/agents/casual_agent.py",
        "purpose": "朋友式 chat — 關心生活、empathy、輕鬆 banter。唔涉及 medical/product",
        "tools": ["(no external — pure LLM)"],
        "kb": [],
        "prompt_attr": "_SYSTEM",
        "max_tokens_attr": None,
    },
    {
        "name": "FAQ Agent",
        "key": "faq",
        "override_key": "faq_system",
        "module": faq_agent,
        "model_attr": "DEFAULT_MODEL",
        "file": "src/agents/faq_agent.py",
        "purpose": "TCM 知识问答 / 食谱清单。KB 检索 + LLM 抽 facts，automatic 穴位图 surface",
        "tools": [
            "KBSearch (hybrid keyword + pgvector semantic)",
            "RecipeExtractor (128 free recipes)",
            "AcupointImageMap (24 points + images / videos)",
        ],
        "kb": ["data/knowledge_base/* (52 cards)"],
        "prompt_attr": "_SYSTEM",
        "max_tokens_attr": None,
    },
    {
        "name": "Sales Agent",
        "key": "sales",
        "override_key": "sales_system",
        "module": sales_agent,
        "model_attr": "DEFAULT_MODEL",
        "file": "src/agents/sales_agent.py",
        "purpose": "Pitch 付费产品。Playbook-driven category match → safety+方向 tone → consultation backstop",
        "tools": [
            "ProductCatalog (13 paid products)",
            "PromotionsLoader (3 offers, multi-stage)",
            "PitchPlaybook (8 condition categories)",
        ],
        "kb": ["data/products/*", "data/promotions/pitch_playbook.json"],
        "prompt_attr": "_SYSTEM",
        "max_tokens_attr": None,
    },
    {
        "name": "Constitution Agent",
        "key": "constitution",
        "override_key": "constitution_vision_system",
        "module": constitution_agent,
        "model_attr": "DEFAULT_MODEL",
        "file": "src/agents/constitution_agent.py",
        "purpose": "九体质评估，4-phase (ask_tongue → vision → 4 MCQs → declare with probability ranking)",
        "tools": [
            "Vision (脷相)",
            "RecipeExtractor (free recipe pitch)",
            "ProductCatalog",
            "KBSearch (hybrid)",
            "PromotionsLoader",
        ],
        "kb": [
            "data/knowledge_base/constitution/* (4 cards)",
            "data/knowledge_base/soups/tcm_food_therapy_soups*.json (128 recipes)",
        ],
        "prompt_attr": "_VISION_SYSTEM",
        "max_tokens_attr": None,
    },
    {
        "name": "Appointment Agent",
        "key": "appointment",
        "module": appointment_agent,
        "model_attr": None,
        "file": "src/agents/appointment_agent.py",
        "purpose": "预约 4-phase (mode → district → slot → confirm)。Rule-based，无 LLM",
        "tools": ["ClinicMatcher (district adjacency)", "PromotionsLoader"],
        "kb": ["data/clinics/clinics.json"],
        "prompt_attr": None,
        "max_tokens_attr": None,
    },
    {
        "name": "Writer",
        "key": "writer",
        "override_key": "writer_system",
        "module": writer,
        "model_attr": "DEFAULT_MODEL",
        "file": "src/agents/writer.py",
        "purpose": "Single voice — 组合所有 specialist output → 1-5 个 WhatsApp bubble + media_to_send",
        "tools": ["(none — reads payload only)"],
        "kb": [],
        "prompt_renderer": "writer._build_system_prompt",
        "max_tokens_attr": None,
    },
]


def _resolve_prompt(meta: dict[str, Any]) -> str:
    mod = meta["module"]
    renderer = meta.get("prompt_renderer")
    if renderer:
        # form like "writer._build_system_prompt"
        fn_name = renderer.split(".")[-1]
        fn = getattr(mod, fn_name, None)
        if callable(fn):
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001
                return f"(render failed: {exc})"
    attr = meta.get("prompt_attr")
    if attr:
        return str(getattr(mod, attr, "(prompt attr missing)"))
    return "(no prompt — rule-based agent)"


def _resolve_model(meta: dict[str, Any]) -> str:
    mod = meta["module"]
    attr = meta.get("model_attr")
    if not attr:
        return "n/a (rule-based)"
    return str(getattr(mod, attr, "?"))


@router.get("/admin", response_class=HTMLResponse)
async def admin_index() -> HTMLResponse:
    cards = []
    overrides = prompt_overrides.get_all()
    for meta in _AGENT_META:
        model = _resolve_model(meta)
        baked_prompt = _resolve_prompt(meta)
        ov_key = meta.get("override_key", "")
        live_override = overrides.get(ov_key, "") if ov_key else ""
        live_prompt = live_override if live_override else baked_prompt
        is_overridden = bool(live_override and live_override.strip())

        tools_html = "".join(
            f'<span class="tag tool">{html.escape(t)}</span>' for t in meta["tools"]
        ) or '<span class="tag muted">(无)</span>'
        kb_html = "".join(
            f'<span class="tag kb">{html.escape(k)}</span>' for k in meta["kb"]
        ) or '<span class="tag muted">(none)</span>'

        # Edit form — only if override_key exists for this agent
        edit_html = ""
        if ov_key:
            status_pill = (
                '<span class="pill" style="background:#ffe0b2;color:#7c2d12;">● overridden (live)</span>'
                if is_overridden
                else '<span class="pill gray">baked-in</span>'
            )
            edit_html = f"""
            <details>
              <summary>📝 Live System Prompt {status_pill}</summary>
              <div class="body">
                <form onsubmit="return savePrompt(event, '{ov_key}')">
                  <textarea name="value" rows="22" style="width:100%;font-family:ui-monospace,monospace;font-size:0.82rem;padding:0.6rem;border:1px solid var(--line);border-radius:6px;">{html.escape(live_prompt)}</textarea>
                  <div style="margin-top:0.5rem;display:flex;gap:0.5rem;align-items:center;">
                    <button type="submit" style="background:var(--accent);color:white;border:0;padding:0.5rem 1rem;border-radius:6px;cursor:pointer;">💾 Save (live)</button>
                    <button type="button" onclick="resetPrompt('{ov_key}')" style="background:#e5e7eb;border:0;padding:0.5rem 1rem;border-radius:6px;cursor:pointer;">↺ Revert to baked-in</button>
                    <span class="sub" id="status-{ov_key}" style="margin:0;"></span>
                  </div>
                </form>
              </div>
            </details>
            """

        cards.append(f"""
        <div class="card">
          <div style="display:flex;align-items:baseline;gap:0.6rem;">
            <h2 style="margin:0;border:0;padding:0;">{html.escape(meta["name"])}</h2>
            <span class="pill gray">{html.escape(model)}</span>
          </div>
          <div class="sub">{html.escape(meta["purpose"])}</div>
          <div class="kv">
            <div class="k">File</div><div><code>{html.escape(meta["file"])}</code></div>
            <div class="k">Tools</div><div>{tools_html}</div>
            <div class="k">Knowledge / data</div><div>{kb_html}</div>
          </div>
          {edit_html}
        </div>
        """)

    data_section = _render_data_sections()

    body = f"""
    <h1>Agent Config Inspector</h1>
    <div class="sub">7 个 agent + 跑落 data。Agent prompts <strong>live-editable</strong> — save 之后即刻喺下一 turn 生效，唔使 redeploy。Data + playbook 改 JSON 直接 push。</div>

    <script>
    async function savePrompt(event, key) {{
      event.preventDefault();
      const form = event.target;
      const value = form.value.value;
      const status = document.getElementById('status-' + key);
      status.textContent = '⏳ saving…'; status.style.color = '';
      try {{
        const r = await fetch('/admin/api/prompts/' + key, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ value }}),
        }});
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const d = await r.json();
        status.textContent = '✓ saved (' + d.length + ' chars) — next turn uses this';
        status.style.color = 'var(--accent)';
      }} catch (e) {{
        status.textContent = '✗ ' + e.message;
        status.style.color = 'var(--warn)';
      }}
      return false;
    }}
    async function resetPrompt(key) {{
      if (!confirm('Revert to baked-in prompt? This deletes the override.')) return;
      const status = document.getElementById('status-' + key);
      status.textContent = '⏳ reverting…';
      try {{
        const r = await fetch('/admin/api/prompts/' + key, {{
          method: 'DELETE',
        }});
        if (!r.ok) throw new Error('HTTP ' + r.status);
        status.textContent = '✓ reverted — reloading…';
        status.style.color = 'var(--accent)';
        setTimeout(() => location.reload(), 600);
      }} catch (e) {{
        status.textContent = '✗ ' + e.message;
        status.style.color = 'var(--warn)';
      }}
    }}
    </script>

    <div class="card">
      <h3 style="margin-top:0;">Specialist Routing Menu (Planner 见到嘅)</h3>
      <pre>{html.escape(render_specialist_menu_zh())}</pre>
    </div>

    <h2>Agents</h2>
    {''.join(cards)}

    <h2>Data & Playbooks</h2>
    <div class="sub">All these JSON live in <code>data/</code>. Editing them = changing behaviour without code.</div>
    {data_section}
    """
    return HTMLResponse(_wrap_page("Agent Config", "agents", body))


# -------------------------------------------------------------------
# Data & Playbook section rendering
# -------------------------------------------------------------------


def _render_data_sections() -> str:
    parts: list[str] = []

    # --- Pitch Playbook ---
    try:
        pb = PitchPlaybook()
        cat_rows = []
        for c in pb.categories:
            cat_rows.append(
                f"<tr><td><code>{html.escape(c.key)}</code></td>"
                f"<td>{html.escape('、'.join(c.keywords))}</td>"
                f"<td>{html.escape('、'.join(c.soup_ids) or '—')}</td>"
                f"<td>{html.escape('、'.join(c.ointment_ids) or '—')}</td>"
                f"<td>{html.escape(c.pitch_angle)}</td></tr>"
            )
        parts.append(f"""
        <div class="card">
          <h3 style="margin-top:0;">🎯 Pitch Playbook
            <span class="pill gray">data/promotions/pitch_playbook.json</span></h3>
          <div class="sub">Sales Agent 嘅 condition-→-product 决定表 + 软性 tone 规则</div>
          <div class="kv" style="margin-bottom:0.8rem;">
            <div class="k">Safety disclaimer</div><div>「{html.escape(pb.safety_disclaimer)}」</div>
            <div class="k">Consultation backstop</div><div>「{html.escape(pb.consultation_backstop)}」</div>
            <div class="k">Tone rule</div><div>{html.escape(pb.global_rules.get('tone',''))}</div>
          </div>
          <table>
            <thead><tr><th>category</th><th>keywords</th><th>soups</th><th>ointments</th><th>方向 / pitch angle</th></tr></thead>
            <tbody>{''.join(cat_rows)}</tbody>
          </table>
        </div>""")
    except Exception as exc:  # noqa: BLE001
        parts.append(f'<div class="card"><span class="tag red">playbook load failed: {html.escape(str(exc))}</span></div>')

    # --- Active Offers ---
    try:
        pl = PromotionsLoader()
        all_offers = pl.all_offers()
        rows = []
        for o in all_offers:
            # Re-load raw record from JSON for trigger_stages + positioning
            stages = "—"
            positioning = "—"
            role = "—"
            for raw in pl._offers_raw:  # noqa: SLF001
                if raw.get("id") == o.id:
                    stages_l = raw.get("trigger_stages") or [raw.get("trigger_stage", "")]
                    stages = ", ".join(s for s in stages_l if s)
                    positioning = raw.get("positioning", "")
                    role = raw.get("role", "")
                    break
            rows.append(f"""<tr>
              <td><code>{html.escape(o.id)}</code></td>
              <td><strong>{html.escape(o.title_zh)}</strong><br/><span class="tag muted">{html.escape(role)}</span></td>
              <td>{html.escape(o.description_zh)}</td>
              <td>{html.escape(positioning)}</td>
              <td><span class="tag muted">{html.escape(stages)}</span></td>
            </tr>""")
        parts.append(f"""
        <div class="card">
          <h3 style="margin-top:0;">🏷️ Active Offers
            <span class="pill gray">data/promotions/active_offers.json</span></h3>
          <div class="sub">3 promotion hooks + 边几个 conversational stage 会 surface</div>
          <table>
            <thead><tr><th>id</th><th>title / role</th><th>desc</th><th>positioning</th><th>trigger_stages</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
          </table>
        </div>""")
    except Exception as exc:  # noqa: BLE001
        parts.append(f'<div class="card"><span class="tag red">offers load failed: {html.escape(str(exc))}</span></div>')

    # --- Product Catalog ---
    try:
        cat = ProductCatalog()
        soup_rows = []
        oint_rows = []
        for p in cat.all_products:
            row = (
                f"<tr><td><code>{html.escape(p.product_id)}</code></td>"
                f"<td><strong>{html.escape(p.name)}</strong></td>"
                f"<td>${p.price_hkd}</td>"
                f"<td>{html.escape('、'.join((p.indications or [])[:4]))}</td>"
                f"<td>{html.escape('、'.join(p.constitution_match or []))}</td>"
                f"<td>{html.escape('、'.join((p.contraindications or [])[:3]) or '—')}</td></tr>"
            )
            (soup_rows if p.product_type == "soup" else oint_rows).append(row)
        parts.append(f"""
        <div class="card">
          <h3 style="margin-top:0;">🍲 Product Catalog
            <span class="pill gray">data/products/*.json</span></h3>
          <details open><summary><strong>湯水 ({len(soup_rows)} 款)</strong></summary>
            <div class="body"><table><thead><tr><th>id</th><th>name</th><th>$</th><th>indications</th><th>constitution_match</th><th>contraindications</th></tr></thead><tbody>{''.join(soup_rows)}</tbody></table></div></details>
          <details><summary><strong>藥膏 ({len(oint_rows)} 款)</strong></summary>
            <div class="body"><table><thead><tr><th>id</th><th>name</th><th>$</th><th>indications</th><th>constitution_match</th><th>contraindications</th></tr></thead><tbody>{''.join(oint_rows)}</tbody></table></div></details>
        </div>""")
    except Exception as exc:  # noqa: BLE001
        parts.append(f'<div class="card"><span class="tag red">catalog load failed: {html.escape(str(exc))}</span></div>')

    # --- Acupoint Library ---
    try:
        am = AcupointImageMap()
        rows = []
        for pt in am.all_points:
            img_tag = '<span class="tag green">✓</span>' if pt.image_path else '<span class="tag muted">—</span>'
            vid_tag = '<span class="tag green">✓</span>' if pt.video_path else '<span class="tag muted">—</span>'
            rows.append(
                f"<tr><td><strong>{html.escape(pt.zh)}</strong></td>"
                f"<td>{html.escape('、'.join(pt.aliases))}</td>"
                f"<td>{img_tag}</td><td>{vid_tag}</td></tr>"
            )
        img_n = sum(1 for pt in am.all_points if pt.image_path)
        vid_n = sum(1 for pt in am.all_points if pt.video_path)
        parts.append(f"""
        <div class="card">
          <h3 style="margin-top:0;">📍 Acupoint Library
            <span class="pill gray">data/acupoints/index.json</span></h3>
          <div class="sub">{len(am.all_points)} 个穴位 · {img_n} 张图 · {vid_n} 个 video</div>
          <details><summary>Show table</summary><div class="body"><table>
            <thead><tr><th>穴位</th><th>aliases</th><th>image</th><th>video</th></tr></thead>
            <tbody>{''.join(rows)}</tbody>
          </table></div></details>
        </div>""")
    except Exception as exc:  # noqa: BLE001
        parts.append(f'<div class="card"><span class="tag red">acupoint load failed: {html.escape(str(exc))}</span></div>')

    # --- KB + Recipes summary ---
    try:
        kb = KBIndex.load()
        rx = RecipeExtractor()
        by_dom: dict[str, int] = {}
        for c in kb.all_cards():
            by_dom[c.domain] = by_dom.get(c.domain, 0) + 1
        dom_tags = "".join(
            f'<span class="tag kb">{html.escape(d)}: {n}</span>'
            for d, n in sorted(by_dom.items())
        )
        parts.append(f"""
        <div class="card">
          <h3 style="margin-top:0;">📚 Knowledge Base + Recipes
            <span class="pill gray">data/knowledge_base/</span></h3>
          <div class="kv">
            <div class="k">Total cards</div><div>{len(kb)}</div>
            <div class="k">By domain</div><div>{dom_tags}</div>
            <div class="k">Trigger phrases (inverted index)</div><div>{len(kb.all_phrases())} unique terms</div>
            <div class="k">Free recipes (extracted)</div><div>{rx.all_count()} ({len(rx._by_constitution)} 体质 covered)</div>
          </div>
        </div>""")
    except Exception as exc:  # noqa: BLE001
        parts.append(f'<div class="card"><span class="tag red">KB load failed: {html.escape(str(exc))}</span></div>')

    # --- 9 Constitutions ---
    cons_tags = "".join(
        f'<span class="tag kb">{html.escape(c.value)}</span>'
        for c in Constitution if c != Constitution.UNKNOWN
    )
    parts.append(f"""
    <div class="card">
      <h3 style="margin-top:0;">🧬 Constitutions (九體質)</h3>
      <div class="sub">Constitution Agent 嘅评估输出空间 + Writer / Sales tone 计算用</div>
      <div>{cons_tags}</div>
    </div>""")

    return "".join(parts)


# -------------------------------------------------------------------
# /admin/traces — list + drill-down
# -------------------------------------------------------------------


def _get_trace_writer(request: Request) -> TraceWriter:
    return request.app.state.trace_writer


def _trace_root(request: Request) -> Path:
    return Path(_get_trace_writer(request)._root)  # noqa: SLF001


@router.post("/admin/api/prompts/{key}")
async def save_prompt(key: str, request: Request) -> JSONResponse:
    """Save a live prompt override. Empty value deletes."""
    body = await request.json()
    value = (body.get("value") or "").strip()
    if not value:
        prompt_overrides.set_override(key, "")
        return JSONResponse({"key": key, "length": 0, "cleared": True})
    prompt_overrides.set_override(key, value)
    return JSONResponse({"key": key, "length": len(value), "cleared": False})


@router.delete("/admin/api/prompts/{key}")
async def delete_prompt(key: str) -> JSONResponse:
    """Clear a prompt override → fall back to baked-in."""
    prompt_overrides.set_override(key, "")
    return JSONResponse({"key": key, "cleared": True})


@router.get("/admin/traces", response_class=HTMLResponse)
async def traces_list(request: Request, phone: str | None = None) -> HTMLResponse:
    tw = _get_trace_writer(request)
    paths = tw.list_recent(phone=phone, limit=50)

    rows = []
    root = _trace_root(request)
    for p in paths:
        turn_id = p.stem
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        ts = _to_hkt(data.get("received_at") or "")
        phone_v = data.get("phone", "?")
        user_msg = (data.get("user_message") or "")[:60]
        specs = ", ".join(
            s.get("name", "?") for s in (data.get("specialists") or [])
        ) or "—"
        n_bubbles = len(((data.get("writer") or {}).get("output") or {}).get("bubbles") or [])
        latency = data.get("total_latency_ms", "?")
        rel = p.relative_to(root)
        rows.append(f"""<tr>
          <td><a href="/admin/traces/{html.escape(turn_id)}"><code>{html.escape(turn_id[:10])}</code></a></td>
          <td>{html.escape(ts)}</td>
          <td>{html.escape(str(phone_v))}</td>
          <td>{html.escape(user_msg)}</td>
          <td>{html.escape(specs)}</td>
          <td>{n_bubbles}</td>
          <td>{latency} ms</td>
          <td><span class="tag muted">{html.escape(str(rel))}</span></td>
        </tr>""")

    phone_input = html.escape(phone or "")
    body = f"""
    <h1>Recent Turns ({len(paths)})</h1>
    <div class="sub">每个 turn 嘅 planner / specialists / writer 详情。点 turn_id 入去睇。</div>
    <form style="margin: 0.8rem 0;">
      <input type="text" name="phone" placeholder="filter by phone, e.g. +85291234567"
        value="{phone_input}" style="padding:0.4rem 0.6rem;border:1px solid var(--line);border-radius:6px;width:280px;">
      <button type="submit" style="padding:0.4rem 0.8rem;background:var(--accent);color:white;border:0;border-radius:6px;">Filter</button>
      <a href="/admin/traces" style="margin-left:0.6rem;font-size:0.85rem;">Clear</a>
    </form>
    <div class="card">
      <table>
        <thead><tr>
          <th>turn_id</th><th>at (HKT)</th><th>phone</th><th>message</th>
          <th>specialists</th><th>bubbles</th><th>latency</th><th>path</th>
        </tr></thead>
        <tbody>{''.join(rows) or '<tr><td colspan="8" style="text-align:center;color:var(--muted);">(no traces yet)</td></tr>'}</tbody>
      </table>
    </div>
    """
    return HTMLResponse(_wrap_page("Traces", "traces", body))


@router.get("/admin/traces/{turn_id}", response_class=HTMLResponse)
async def trace_detail(request: Request, turn_id: str) -> HTMLResponse:
    tw = _get_trace_writer(request)
    bundle = tw.read(turn_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail=f"no trace for turn_id={turn_id}")

    d = bundle.model_dump(mode="json")
    return HTMLResponse(_wrap_page(
        f"Trace · {turn_id[:10]}", "traces", _render_trace_detail(d, turn_id),
    ))


def _render_trace_detail(d: dict[str, Any], turn_id: str) -> str:
    # ── Header / CRM
    received = _to_hkt(d.get("received_at") or "")
    user_msg = d.get("user_message") or ""
    crm = d.get("crm_snapshot") or {}
    crm_kv = "\n".join(
        f"  {k}: {v}"
        for k, v in [
            ("status", crm.get("status")),
            ("constitution", crm.get("constitution")),
            ("name", crm.get("name") or "(unknown)"),
            ("district", crm.get("district") or "—"),
            ("pain_points", crm.get("pain_points")),
            ("products_pitched", crm.get("products_pitched")),
            ("appointments_count", len(crm.get("appointments") or [])),
            ("history_msg_count", len(crm.get("conversation_history") or [])),
            ("temp_state_keys", list((crm.get("temp_state") or {}).keys())),
        ]
        if v is not None
    )

    # ── Planner
    planner_step = d.get("planner") or {}
    p_in = planner_step.get("input", {})
    p_out = planner_step.get("output", {})
    planner_block = f"""
    <div class="card">
      <h2 style="margin-top:0;">🧭 Planner <span class="pill">{html.escape(planner_step.get('model','?'))}</span></h2>
      <div class="kv">
        <div class="k">specialists</div><div><strong>{', '.join(p_out.get('specialists') or [])}</strong></div>
        <div class="k">mode</div><div><span class="tag green">{html.escape(p_out.get('mode','?'))}</span></div>
        <div class="k">reasoning</div><div>{html.escape(p_out.get('reasoning',''))}</div>
        <div class="k">notes_for_writer</div><div>{html.escape(p_out.get('notes_for_writer','') or '(none)')}</div>
        <div class="k">proactive_hint</div><div>{html.escape(p_out.get('proactive_hint','') or '(none)')}</div>
        <div class="k">latency</div><div>{planner_step.get('latency_ms',0)} ms</div>
        <div class="k">tokens</div><div>in={planner_step.get('input_tokens',0)} / out={planner_step.get('output_tokens',0)}</div>
      </div>
    </div>
    """

    # ── Specialists
    spec_blocks = []
    for s in d.get("specialists") or []:
        name = s.get("name", "?")
        payload = s.get("output", {}).get("payload", {}) if isinstance(s.get("output"), dict) else {}
        tools = s.get("tools_called") or []
        cards = s.get("cards_read") or []
        tools_html = "".join(
            f'<details><summary>🛠 {html.escape(t.get("name","?"))}</summary>'
            f'<div class="body"><pre>{html.escape(json.dumps(t, ensure_ascii=False, indent=2))}</pre></div></details>'
            for t in tools
        ) or '<span class="tag muted">no tools called</span>'
        cards_html = "".join(
            f'<span class="tag kb">{html.escape(c)}</span>' for c in cards
        ) or '<span class="tag muted">no cards</span>'
        err = s.get("error")
        err_html = f'<div class="tag red">ERROR: {html.escape(str(err))}</div>' if err else ""

        spec_blocks.append(f"""
        <div class="card">
          <h2 style="margin-top:0;">🤖 {html.escape(name).upper()} <span class="pill gray">{html.escape(s.get('model','?'))}</span></h2>
          {err_html}
          <div class="kv">
            <div class="k">latency</div><div>{s.get('latency_ms',0)} ms</div>
            <div class="k">tokens</div><div>in={s.get('input_tokens',0)} / out={s.get('output_tokens',0)}</div>
            <div class="k">cards read</div><div>{cards_html}</div>
          </div>
          <h3>Tools called</h3>{tools_html}
          <details><summary>Full payload</summary><div class="body"><pre class="scroll">{html.escape(json.dumps(payload, ensure_ascii=False, indent=2))}</pre></div></details>
        </div>
        """)

    spec_html = "".join(spec_blocks) or '<div class="card"><span class="tag muted">no specialists ran</span></div>'

    # ── Writer
    w = d.get("writer") or {}
    w_out = (w.get("output") or {})
    bubbles = w_out.get("bubbles") or []
    media = w_out.get("media_to_send") or []
    bubbles_html = "<br>".join(
        f'<div class="bubble">{html.escape(b)}</div>' for b in bubbles
    ) or '<span class="tag muted">no bubbles</span>'
    media_html = "<br>".join(
        f'<div><span class="tag tool">after_bubble_idx={m.get("after_bubble_idx","?")}</span>'
        f' <code>{html.escape(str(m.get("url","")))}</code></div>'
        for m in media
    ) or '<span class="tag muted">no media</span>'

    writer_block = f"""
    <div class="card">
      <h2 style="margin-top:0;">✍️ Writer <span class="pill writer">{html.escape(w.get('model','?'))}</span></h2>
      <div class="kv">
        <div class="k">latency</div><div>{w.get('latency_ms',0)} ms</div>
        <div class="k">tokens</div><div>in={w.get('input_tokens',0)} / out={w.get('output_tokens',0)}</div>
      </div>
      <h3>Bubbles sent</h3>
      <div>{bubbles_html}</div>
      <h3>Media attached</h3>
      <div>{media_html}</div>
    </div>
    """

    # ── CRM diff
    diff = d.get("crm_diff") or {}
    if diff:
        diff_rows = "".join(
            f"<tr><td><code>{html.escape(k)}</code></td>"
            f"<td><pre style=\"margin:0;\">{html.escape(json.dumps(v.get('before'), ensure_ascii=False))}</pre></td>"
            f"<td><pre style=\"margin:0;\">{html.escape(json.dumps(v.get('after'), ensure_ascii=False))}</pre></td></tr>"
            for k, v in diff.items()
        )
        diff_html = f"<table><thead><tr><th>field</th><th>before</th><th>after</th></tr></thead><tbody>{diff_rows}</tbody></table>"
    else:
        diff_html = '<span class="tag muted">no CRM mutation this turn</span>'

    # ── Send log
    sends = d.get("send_log") or []
    send_html = (
        "<table><tr><th>idx</th><th>text</th><th>media</th><th>sent_at</th><th>wa_msg_id</th></tr>"
        + "".join(
            f"<tr><td>{s.get('bubble_idx','?')}</td><td>{html.escape(s.get('text','')[:80])}</td>"
            f"<td>{html.escape(str(s.get('media_url','')))}</td>"
            f"<td>{html.escape(str(s.get('sent_at','')))}</td>"
            f"<td>{html.escape(str(s.get('wa_message_id','')))}</td></tr>"
            for s in sends
        )
        + "</table>"
    ) if sends else '<span class="tag muted">no send log (dev mode or pre-send error)</span>'

    fatal = d.get("fatal_error")
    fatal_html = (
        f'<div class="card" style="background:#fce4dc;color:#c44d3a;"><strong>⚠️ FATAL:</strong> '
        f'<code>{html.escape(str(fatal))}</code></div>' if fatal else ""
    )

    return f"""
    <a href="/admin/traces" style="font-size:0.9rem;">← all traces</a>
    <h1>Turn <code>{html.escape(turn_id)}</code></h1>
    <div class="sub">{html.escape(received)} HKT · {html.escape(str(d.get('phone','?')))} · {d.get('total_latency_ms',0)} ms total</div>
    {fatal_html}

    <div class="card">
      <h2 style="margin-top:0;">👤 User Message</h2>
      <div class="bubble user">{html.escape(user_msg)}</div>
      {f'<div class="sub">merged from: {", ".join(d.get("merged_from_fragments") or [])}</div>' if d.get("merged_from_fragments") else ""}
      {f'<div class="sub">media URLs: {", ".join(d.get("media_urls") or [])}</div>' if d.get("media_urls") else ""}
      <h3>CRM Snapshot (pre-turn)</h3>
      <pre>{html.escape(crm_kv)}</pre>
    </div>

    {planner_block}

    <h2>Specialists ({len(d.get('specialists') or [])})</h2>
    {spec_html}

    {writer_block}

    <div class="card">
      <h2 style="margin-top:0;">📤 Send Log</h2>{send_html}
    </div>
    <div class="card">
      <h2 style="margin-top:0;">🔄 CRM Diff</h2>{diff_html}
    </div>
    <div class="card">
      <details><summary>Raw bundle (debug)</summary>
        <div class="body"><pre class="scroll">{html.escape(json.dumps(d, ensure_ascii=False, indent=2))}</pre></div>
      </details>
    </div>
    """
