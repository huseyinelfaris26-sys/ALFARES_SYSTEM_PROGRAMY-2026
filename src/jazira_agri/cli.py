from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path

from .advisor.diagnose import diagnose
from .advisor.recommend import recommend
from .auth import validate_credentials
from .core.configuration import get_settings
from .knowledge.loader import load_crops, load_diseases


def _show(obj: object) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jazira")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("crops", help="list crops")
    sub.add_parser("symptoms", help="list valid symptom keys")
    sub.add_parser("config", help="show redacted application configuration")
    sub.add_parser("status", help="show application and database configuration status")
    sub.add_parser("login", help="check credentials interactively")

    rec = sub.add_parser("recommend", help="seed, fertilizer and expected-yield advice")
    rec.add_argument("--crop", required=True)
    rec.add_argument("--farming", required=True, choices=["rainfed", "irrigated"])
    rec.add_argument("--region", default="tal_abyad")
    rec.add_argument("--rain", type=float)
    rec.add_argument("--ec", type=float)

    diag = sub.add_parser("diagnose", help="diagnose from photo and symptoms")
    diag.add_argument("--crop", required=True)
    diag.add_argument("--photo", type=Path)
    diag.add_argument("--symptoms", default="")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "crops":
            for key, crop in load_crops().items():
                print(f"{key}: {crop['name_ar']} / {crop['name_en']}")
        elif args.cmd == "symptoms":
            for key, label in load_diseases()["symptoms"].items():
                print(f"{key}: {label}")
        elif args.cmd == "recommend":
            _show(recommend(args.crop, args.farming, args.region, args.rain, args.ec))
        elif args.cmd == "diagnose":
            symptoms = [item.strip() for item in args.symptoms.split(",") if item.strip()]
            _show(diagnose(args.crop, symptoms, args.photo))
        elif args.cmd == "config":
            _show(get_settings().as_dict())
        elif args.cmd == "status":
            settings = get_settings()
            _show({"app": settings.app_name, "environment": settings.app_env,
                   "default_knowledge": settings.default_knowledge,
                   "database_configured": bool(settings.database_url or settings.db_password)})
        elif args.cmd == "login":
            username = input("Username: ").strip()
            password = getpass.getpass("Password: ")
            if not validate_credentials(username, password):
                print("Authentication failed", file=sys.stderr)
                return 1
            print("Authenticated")
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
