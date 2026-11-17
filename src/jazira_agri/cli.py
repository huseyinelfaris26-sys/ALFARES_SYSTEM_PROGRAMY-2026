"""Command line: jazira crops | recommend | diagnose | symptoms | config | status | login."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .advisor.diagnose import diagnose
from .advisor.recommend import recommend
from .auth import build_auth_payload
from .core.configuration import get_settings
from .knowledge.loader import load_crops, load_diseases


def _show(obj: object) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="jazira")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("crops", help="list crops")
    sub.add_parser("symptoms", help="list valid symptom keys")
    sub.add_parser("config", help="show application configuration")
    sub.add_parser("status", help="show app status")
    sub.add_parser("login", help="validate configured user and print auth payload")

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

    l = sub.add_parser("login", help="validate configured user and print auth payload")
    l.add_argument("--username", default=None)
    l.add_argument("--password", default=None)

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
        elif a.cmd == "config":
            _show(get_settings().as_dict())
        elif a.cmd == "status":
            _show({
                "app_name": get_settings().app_name,
                "default_knowledge": get_settings().default_knowledge,
                "environment": get_settings().app_env,
                "database": {
                    "host": get_settings().db_host,
                    "port": get_settings().db_port,
                    "name": get_settings().db_name,
                },
            })
        elif a.cmd == "login":
            username = a.username or get_settings().username
            password = a.password or get_settings().password
            _show(build_auth_payload(username, password))
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
