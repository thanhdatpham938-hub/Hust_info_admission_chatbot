"""Bo ca co nhan AC2/AC8 da duoc nguoi dung duyet (backend/tests/eval/entity_cases.csv) — khong can DB.

Moi ca da duyet phai dung. Ca nao do thi KHONG sua nhan cho khop code: hoac sua code/alias, hoac
hoi nguoi dung sua nhan. So do % chi tiet: python scripts/eval_entity_cases.py
"""

import csv

import pytest

from app.core.config import ROOT

CASES = [r for r in csv.DictReader((ROOT / "backend" / "tests" / "eval" / "entity_cases.csv")
                                   .open(encoding="utf-8-sig", newline="")) if r["duyet"].strip()]


@pytest.mark.parametrize("case", CASES, ids=[f"{c['id']}-{c['mention'].strip()}" for c in CASES])
def test_ca_da_duyet(ctx, case):
    res = ctx.resolve(case["mention"], case["entity_type"], [int(case["year"])] if case["year"] else None)
    got = {res.group_code} if res.group_code else set(res.codes)
    want = {c for c in case["expected_codes"].split(";") if c}
    assert (res.status, got) == (case["expected_status"], want), case["note"]
