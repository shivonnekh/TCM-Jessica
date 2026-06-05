"""Non-WhatsApp inbound channels for Jessica.

Currently:
    * Instagram DM + comment (Meta Graph API webhooks)  → ``instagram.py``

Facebook Messenger shares Meta's webhook + Graph API shape, so the
``meta_events`` parser and ``meta_client`` sender are written to handle
both ``object == "instagram"`` and ``object == "page"`` payloads. A
``facebook.py`` router can be added later with near-zero new code.

Design parity with ``src/whatsapp/``:
    meta_events.py  ~ whatsapp/models.py   (parse + immutable models)
    meta_client.py  ~ whatsapp/client.py   (outbound API)
    instagram.py    ~ whatsapp/router.py   (webhook + dispatch glue)

All channels dispatch into the SAME ``JessicaPipeline.run_turn`` using a
namespaced CRM key so each surface keeps its own user records:
    WhatsApp DM      phone digits        "85291234567"
    WhatsApp group   "g_<sender_lid>"
    Instagram        "ig_<igsid>"
    Facebook page    "fb_<psid>"
"""
