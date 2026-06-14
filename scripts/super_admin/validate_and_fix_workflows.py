#!/usr/bin/env python3
"""
Audit and optionally repair WhatsApp workflow definitions in MongoDB.

Validates every saved workflow (registered handlers, END step, tenant caps).
With --fix, rewrites known legacy placeholder steps (e.g. SHOW_CATEGORIES → BROWSE_CATALOG,
SHOW_PRODUCTS → CHECK_PRODUCT). Validates registered handlers including SHOW_SERVICE_PRICES.

Usage (from project root):
  python scripts/super_admin/validate_and_fix_workflows.py
  python scripts/super_admin/validate_and_fix_workflows.py --tenant ss_business_store
  python scripts/super_admin/validate_and_fix_workflows.py --fix
  python scripts/super_admin/validate_and_fix_workflows.py --tenant ss_business_store --fix --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.db import get_db
from app.services.whatsapp.workflow.workflow_migrator import (
    audit_all_workflows,
    audit_tenant_workflows,
    fix_all_workflows,
    fix_tenant_workflows,
)


def _print_audit(items: list) -> int:
    invalid = 0
    for row in items:
        status = "OK" if row["valid"] else "INVALID"
        print(f"\n[{status}] {row['tenant']} / {row['workflow_id']} — {row['name']}")
        if row["errors"]:
            invalid += 1
            for err in row["errors"]:
                print(f"  ✗ {err}")
        if row.get("repair_notes"):
            print("  Repair preview:")
            for note in row["repair_notes"]:
                print(f"    → {note}")
            if row.get("errors_after_repair"):
                print("  Still invalid after repair:")
                for err in row["errors_after_repair"]:
                    print(f"    ✗ {err}")
            elif not row["valid"]:
                print("  ✓ Repair would make this workflow valid (--fix to apply)")
    return invalid


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit/repair WhatsApp workflows in MongoDB")
    parser.add_argument("--tenant", type=str, help="Limit to one tenant id")
    parser.add_argument("--fix", action="store_true", help="Apply automatic repairs where possible")
    parser.add_argument("--dry-run", action="store_true", help="With --fix, show changes without writing")
    args = parser.parse_args()

    get_db()

    if args.fix:
        if args.tenant:
            summary = fix_tenant_workflows(args.tenant, dry_run=args.dry_run)
            print(f"Tenant {args.tenant}: {summary['fixed']}/{summary['total']} repaired, {summary['failed']} failed")
            for r in summary["results"]:
                if r.get("notes"):
                    print(f"  {r['workflow_id']}: {', '.join(r['notes'])}")
                if not r.get("ok"):
                    print(f"  FAILED {r['workflow_id']}: {r.get('errors') or r.get('error')}")
        else:
            summary = fix_all_workflows(dry_run=args.dry_run)
            mode = " (dry-run)" if args.dry_run else ""
            print(f"All tenants{mode}: {summary['fixed']} repaired, {summary['failed']} failed across {summary['tenants']} tenants")
        return

    items = audit_tenant_workflows(args.tenant) if args.tenant else audit_all_workflows()
    if not items:
        print("No workflows found.")
        return

    invalid = _print_audit(items)
    print(f"\nSummary: {len(items)} workflow(s), {invalid} invalid")
    if invalid:
        print("Run with --fix to auto-repair legacy step codes where possible.")
        sys.exit(1)


if __name__ == "__main__":
    main()
