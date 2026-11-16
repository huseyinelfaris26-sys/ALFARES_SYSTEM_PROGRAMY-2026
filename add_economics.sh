})
    return {
        "crop": crop,
        "farming": farming,
        "price_usd_per_kg": price,
        "cost_items_usd": {k: round(v, 2) for k, v in items.items()},
        "total_cost_usd": round(cost, 2),
        "scenarios": scenarios,
        "estimate": econ.get("estimate", True),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="jazira-econ")
    p.add_argument("--crop", required=True)
    p.add_argument("--farming", required=True, choices=["rainfed", "irrigated"])
    p.add_argument("--rain", type=float)
    p.add_argument("--pesticides", default="", help="comma separated ids from the economics file")
    p.add_argument("--yield-kg", help="your own yield range kg/dunum, example 150,250")
    a = p.parse_args(argv)
    try:
        yk = None
        if a.yield_kg:
            lo, hi = (float(x) for x in a.yield_kg.split(","))
            yk = (lo, hi)
        pest = [x.strip() for x in a.pesticides.split(",") if x.strip()]
        res = profit_table(a.crop, a.farming, a.rain, pest, yk)
    except (ValueError, KeyError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"crop={res['crop']} farming={res['farming']}  (USD per dunum, ESTIMATE)")
    for name, value in res["cost_items_usd"].items():
        print(f"  cost {name}: {value}")
    print(f"  TOTAL COST: {res['total_cost_usd']}   price/kg: {res['price_usd_per_kg']}")
    if not res["scenarios"]:
        print("  no yield data for this crop. use --yield-kg low,high")
    for s in res["scenarios"]:
        print(f"  [{s['scenario']}] yield {s['yield_kg']} kg -> revenue {s['revenue_usd']} -> profit {s['profit_usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
EOF

echo
echo "DONE. Try:"
echo "  python -m jazira_agri.advisor.economics --crop wheat --farming rainfed --rain 300"
echo "  python -m jazira_agri.advisor.economics --crop wheat --farming irrigated --pesticides triazole_fungicide"
echo "  python -m jazira_agri.advisor.economics --crop cumin --farming irrigated --yield-kg 40,80"
echo "To edit prices: open data/regions/tal_abyad_economics.json"
