#!/usr/bin/env python3
"""
Seed all industry domains in one go. Runs run_seed_domain for each domain:
salon, clinic, gym, school, store, camp, car_showroom.
Use --force to replace existing data for each tenant.

Usage:
  python scripts/run_seed_all_domains.py
  python scripts/run_seed_all_domains.py --force

After seeding, audit workflows:
  python scripts/super_admin/validate_and_fix_workflows.py
"""
import argparse
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOMAINS = ["salon", "clinic", "gym", "school", "store", "camp", "car_showroom"]


def main():
    parser = argparse.ArgumentParser(description="Seed all industry demo tenants")
    parser.add_argument("--force", action="store_true", help="Replace existing data for each tenant")
    args = parser.parse_args()
    force_flag = ["--force"] if args.force else []
    for domain in DOMAINS:
        cmd = [sys.executable, os.path.join(ROOT, "scripts", "run_seed_domain.py"), "--domain", domain] + force_flag
        print(f"\n--- Seeding {domain} ---")
        r = subprocess.run(cmd, cwd=ROOT)
        if r.returncode != 0:
            print(f"Failed: {domain}")
            sys.exit(r.returncode)
    print("\nDone. All domains seeded.")


if __name__ == "__main__":
    main()
