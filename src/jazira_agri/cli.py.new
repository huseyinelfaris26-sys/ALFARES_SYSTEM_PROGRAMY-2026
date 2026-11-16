"""Command line: jazira crops | recommend | diagnose | symptoms."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .advisor.diagnose import diagnose
from .advisor.recommend import recommend
from .knowledge.loader import load_crops, load_diseases


def _show(obj: object) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="jazira")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("crops", help="list crops")
    sub.add_parser("symptoms", help="list valid symptom keys")

    r = sub.add_parser("recommend", help="seed, fertilizer and yield advice")
    r.add_argument("--crop", required=True)
    r.add_argument("--farming", required=True, choices=["rainfed", "irrigated"])
    r.add_argument("--region", default="tal_abyad")
    r.add_argument("--rain", type=float, help="seasonal rain in mm")
    r.add_argument("--ec", type=float, help="irrigation water EC in dS/m")

    d = sub.add_parser("diagnose", help="diagnose from photo and symptoms")
    d.add_argument("--crop", required=True)
    d.add_argument("--photo", type=Path)
    d.add_argument("--symptoms", default="", help="comma separated keys")

    a = p.parse_args(argv)
    try:
        if a.cmd == "crops":
            for key, c in load_crops().items():
                print(f"{key}: {c['name_ar']} / {c['name_en']}")
        elif a.cmd == "symptoms":
            for key, label in load_diseases()["symptoms"].items():
                print(f"{key}: {label}")
        elif a.cmd == "recommend":
            _show(recommend(a.crop, a.farming, a.region, a.rain, a.ec))
        elif a.cmd == "diagnose":
            syms = [s.strip() for s in a.symptoms.split(",") if s.strip()]
            _show(diagnose(a.crop, syms, a.photo))
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
