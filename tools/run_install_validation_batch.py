#!/usr/bin/env python3
"""Batch live queries against SupportRuntimeService for installation SOP validation."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.container import support_runtime_service  # noqa: E402

# 20 distinct questions: mix of direct SOP topics, paraphrases, typos, Malay, edge cases.
QUESTIONS: list[tuple[str, str]] = [
    ("q01_standard_install", "How do I install KommuAssist? Explain relay, cable routing, Vision mount, and Kommu Power in order."),
    ("q02_usb_ports_informal", "kommu relay which usb goes to vision and which to power — i might have swapped them"),
    ("q03_cluster_adas_error", "After installing the relay I get an ADAS error on the instrument cluster. Vision is unplugged. What should I check first?"),
    ("q04_no_control_paraphrase", "Camera view comes on but I get no steering or ACC control from KommuAssist. Any common wiring mistake?"),
    ("q05_myvi_fingerprint", "What exact vehicle fingerprint string should I use for a Perodua Myvi?"),
    ("q06_controls_waiting", "The device says controls waiting to start — what usually causes that with fingerprints?"),
    ("q07_malay_vision_mount", "Boleh terangkan cara pasang Kommu Vision pada cermin depan dengan pelekat elektrostatik?"),
    ("q08_engine_off_rule", "Should the car engine be on or off when I plug the L-shaped USB into the Vision unit?"),
    ("q09_sticker_position", "Where on the windshield should face '1' of the electrostatic sticker be placed relative to the ADAS cover?"),
    ("q10_cable_routing", "How do we route the long USB-C past the right A-pillar airbag trim and weather strip to the OBD area?"),
    ("q11_kommu_power_obd", "What is Kommu Power and where does it plug in the vehicle?"),
    ("q12_getting_ready_gps", "Device stays on getting ready and never opens camera view with engine on — could this be GPS sync?"),
    ("q13_calibration_invalid", "Calibration invalid — the install doc talks about road and sky ratio. What went wrong and what do I fix?"),
    ("q14_corolla_cross_fp", "What is the fingerprint for Toyota Corolla Cross from the official table?"),
    ("q15_byd_dashcam", "BYD Atto 3 shows unrecognized car / dashcam mode. What fingerprint do I enter?"),
    ("q16_level2_liability", "For customer briefing: how do we explain Level 2 and who is liable?"),
    ("q17_yellow_triangle", "What does the yellow triangle in the driving UI mean for braking and lead car?"),
    ("q18_traffic_lights", "Does bukapilot detect traffic lights, potholes, and speed bumps?"),
    ("q19_software_check_reboot", "After connecting Wi‑Fi and the Software page shows Last Update Check as now, what should the user do next?"),
    ("q20_perodua_malfunction_lamp", "Perodua ADAS malfunction light still on after we reseated the connector — when should it clear?"),
]


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/kai_install_validation_report.json")
    rows: list[dict] = []
    for qid, text in QUESTIONS:
        uid = f"install_val_{qid}"
        r = support_runtime_service.execute(text, lang="EN", user_id=uid)
        rows.append(
            {
                "id": qid,
                "question": text,
                "decision": r.decision,
                "confidence": r.confidence,
                "capability_used": r.capability_used,
                "source_ids": list(r.source_ids or []),
                "answer": (r.answer or "").strip(),
            }
        )
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": "SupportRuntimeService.execute (same stack as /v2/agent/message)",
        "count": len(rows),
        "results": rows,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
