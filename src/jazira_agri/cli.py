"""Command line: jazira crops | recommend | diagnose | symptoms | soil | seeds | pests | indices."""
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
    parser = argparse.ArgumentParser(prog="jazira")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("crops", help="list crops")
    sub.add_parser("symptoms", help="list valid symptom keys")

    rec = sub.add_parser("recommend", help="seed, fertilizer and yield advice")
    rec.add_argument("--crop", required=True)
    rec.add_argument("--farming", required=True, choices=["rainfed", "irrigated"])
    rec.add_argument("--region", default="tal_abyad")
    rec.add_argument("--rain", type=float, help="seasonal rain in mm")
    rec.add_argument("--ec", type=float, help="irrigation water EC in dS/m")

    diag = sub.add_parser("diagnose", help="diagnose from photo and symptoms")
    diag.add_argument("--crop", required=True)
    diag.add_argument("--photo", type=Path)
    diag.add_argument("--symptoms", default="", help="comma-separated symptom keys")

    soil = sub.add_parser("soil", help="assess basic soil indicators")
    soil.add_argument("--ph", type=float, required=True)
    soil.add_argument("--ec", type=float, required=True, help="soil EC in dS/m")
    soil.add_argument("--organic-matter", type=float)
    soil.add_argument("--texture")

    seeds = sub.add_parser("seeds", help="show seed information from local crop data")
    seeds.add_argument("--crop")

    pests = sub.add_parser("pests", help="rank disease candidates from observed symptoms")
    pests.add_argument("--crop", required=True)
    pests.add_argument("--symptoms", default="", help="comma-separated symptom keys")

    indices = sub.add_parser("indices", help="calculate NDVI from scalar RED and NIR values")
    indices.add_argument("--red", type=float, required=True)
    indices.add_argument("--nir", type=float, required=True)

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
        elif args.cmd == "soil":
            from .soil import SoilAnalyzer

            _show(SoilAnalyzer(ph=args.ph, salinity_ec=args.ec, organic_matter=args.organic_matter, texture=args.texture).evaluate())
        elif args.cmd == "seeds":
            from .crops import SeedAdvisor

            _show(SeedAdvisor.recommend(args.crop))
        elif args.cmd == "pests":
            from .advisor import PestAdvisor

            symptoms = [item.strip() for item in args.symptoms.split(",") if item.strip()]
            _show(PestAdvisor().suggest(args.crop, symptoms))
        elif args.cmd == "indices":
            try:
                import numpy as np
                from .geo_spatial import IndexAnalyzer
            except ImportError as exc:
                raise RuntimeError("install optional geospatial dependencies with: pip install 'jazira-agri-os[analysis]'") from exc
            _show({"ndvi": float(IndexAnalyzer.ndvi(np.array(args.red), np.array(args.nir))), "advisory_only": True})
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
