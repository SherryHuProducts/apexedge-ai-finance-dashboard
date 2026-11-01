# ApexEdge | Three code demonstrations for a CFO interview

**Audience:** CFO + Sales VP. **Claim:** I can turn financial policy into working software and explain the controls. **Scope:** Synthetic Amazon and B2B CSV connectors, local SQLite, synthetic GL control; **not** a live marketplace API, production ERP integration, or a trained AI model.

## Run the demonstration (2 minutes)

From the repository root, with Python 3.10+ installed:

```bash
python interview_code_walkthrough.py --repeat
python interview_code_walkthrough.py --fee 20.00 --repeat
python -m unittest discover -s tests -p 'test_interview_code_walkthrough.py'
```

The first command proves a repeated file does not double-count. The second applies a **later synthetic fee correction**: Amazon fee changes from **$24 to $20**, its payout changes from **$96 to $100**, and the independently supplied **original GL control now disagrees by -$4**. The platform fee is still **$2 above** its $18 expected fee. Both differences are valid and mean different things.

## 1. Two sales channels → one trusted financial schema

**Real repository functions:** `thin_slice.py:parse_csv` and `thin_slice.py:cents`.

```python
number = Decimal(str(value).strip())
if not number.is_finite() or number != number.quantize(Decimal("0.01")):
    raise ValueError("Money requires finite values with at most two decimals")
return int(number * 100)
```

```python
row = {
    "channel": channel,
    "record_id": rid,
    "source_file": source_name or f"{channel.lower()}_synthetic.csv",
    "source_row": source_row,
    "order_id": raw["source_order_id"].strip(),
    "sku": raw["sku"].strip(),
    "net_sales_cents": cents(raw["net_sales"]),
    "fee_actual_cents": cents(raw["fee_actual"]),
    "settlement_net_cents": cents(raw["settlement_net"]),
    # ... other validated fields ...
}
```

**In business terms:** marketplace data and B2B invoicing may have different layouts. We map both to the same financial definition; store money as integer cents, and retain the source filename and line number so we can trace any KPI back to a document. The parser rejects missing columns, duplicate IDs, invalid cents, and non-positive quantities rather than guessing.

**What you can modify live:** in `thin_slice.py`, change a simulated source amount from `24.00` to `24.001` and run `python thin_slice.py`; watch the input fail rather than silently rounding. Restore the value to `24.00` afterwards. This is **input validation, not an LLM**.

**One-sentence English explanation:** “I use a canonical schema and exact cent-level arithmetic to combine channels without losing the original source evidence.”

## 2. SQLite database → no duplicates, safe late corrections, audit trail

**Real repository functions:** `thin_slice.py:connect`, `thin_slice.py:ingest`.

```sql
CREATE TABLE IF NOT EXISTS source_rows (
    channel TEXT NOT NULL,
    record_id TEXT NOT NULL,
    -- financial fields, source_file, source_row, updated_at, fingerprint ...
    PRIMARY KEY (channel, record_id)
);

CREATE TABLE IF NOT EXISTS load_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loaded_at TEXT NOT NULL,
    channel TEXT NOT NULL,
    record_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    prior_fingerprint TEXT,
    new_fingerprint TEXT NOT NULL
);
```

```python
if old and row["updated_at"] < old["updated_at"]:
    stale += 1
    continue
if old and row["fingerprint"] == old["fingerprint"]:
    unchanged += 1
    continue
# Then INSERT ... ON CONFLICT(channel, record_id) DO UPDATE,
# and record INSERT or BACKFILL_UPDATE in load_events.
```

**In business terms:** duplicate files must not duplicate revenue. A marketplace refund or fee adjustment arriving a week late may change a past day's provisional margin. The **composite primary key** prevents duplicate financial records; the file fingerprint and source update time distinguish repeat uploads, stale snapshots, and legitimate revisions; `load_events` records what changed. The existing module uses **a SQLite transaction**, so a failed batch does not partially commit.

**What you can modify live:** run `python interview_code_walkthrough.py --repeat`; there remain **two source rows** and **two initial audit events**, even after a duplicate Amazon upload. Then add `--fee 20.00`; there are still two source rows, but a **third audit event** for the correction. Explain why *row count stays constant while version history grows*.

**One-sentence English explanation:** “A rerun cannot double-book sales, and late-arriving fee revisions are traceable instead of silently overwriting history.”

## 3. Finance controls → GL comparison, dollar exceptions, AI evidence

**Real repository functions:** `thin_slice.py:evaluate`, `thin_slice.py:evidence_packet`.

```python
difference = (
    row["net_sales_cents"]
    - row["fee_actual_cents"]
    - row["settlement_net_cents"]
)
# 0 means settlement arithmetic agrees; not proof the fee is correct.

fee_policy_variance = row["fee_actual_cents"] - row["fee_expected_cents"]
gl_fee_variance = total_actual_fees - gl_control["fee_actual_cents"]
```

```python
{"evidence_id": "FEE-001", "baseline": 18.0,
 "observed": 24.0, "difference": 6.0,
 "evidence": ["net_sales", "fee_expected", "fee_actual", "source_updated_at"],
 "cause_status": "unverified"}
```

**In business terms:** these are **three independent tests**, not one margin figure:

| Control | Initial synthetic outcome | CFO meaning |
| --- | --- | --- |
| Settlement arithmetic: sales − fee − payout | $120 − $24 − $96 = **$0 difference** | Platform settlement adds up internally. |
| Fee policy: actual − expected | $24 − $18 = **+$6 unfavorable** | Arithmetic can tie while fee policy is violated. |
| GL fee total − independent GL control | $24 − $24 = **$0 difference** | Source agrees to the supplied demonstration GL control. |

After `--fee 20.00`, settlement arithmetic **still ties**, policy variance becomes **+$2**, but GL fee variance becomes **−$4** until the ledger/control is appropriately updated and reviewed. This distinction is the point of the demo.

**AI's role:** prepare a structured **evidence packet** for an optional language model to describe exceptions and propose review steps. The model receives **no customer/order identifiers** in this packet. It must not post a journal entry, assert a root cause, or change approved cost allocation policy. The supplied deterministic explanation is **not an LLM call**. Four-case deterministic rule evaluation in the repository is **not LLM accuracy validation**.

**One-sentence English explanation:** “My code separates arithmetic reconciliation, policy exceptions, and GL differences; AI can summarize the evidence, but Finance verifies the reason and approves the adjustment.”

## Two-minute English walkthrough for the CFO

> “The business challenge is not building another dashboard. It is making channel profitability trustworthy. First, I standardized a simulated Amazon settlement file and a wholesale invoice file into one schema, preserving source evidence and exact cents. Second, I used a database primary key, fingerprints, and an audit log, so reloading files does not duplicate revenue and later adjustments are traceable. Third, I wrote independent controls for settlement math, expected fees, and the GL. Here, the platform settlement balances, but Amazon still charged six dollars more than expected. When I simulate a late correction to twenty dollars, the policy exception falls to two, while the ledger needs a four-dollar follow-up. AI can produce an evidence-linked explanation, but cannot approve the cause. That is how I connect computer science with accounting judgment and commercial decisions.”

## CFO follow-up questions to rehearse

1. **Why SQLite, not PostgreSQL?** It is sufficient for a reproducible local proof of concept. Production integration would choose a managed DB based on access control, concurrent writers, backup, and IT requirements.
2. **Where is the 'AI'?** Evidence structuring and optional language-model narrative, not the deterministic calculations. I would benchmark a real model against a human-labeled gold set before claiming accuracy.
3. **Does PASS mean the monthly books are closed?** No. `RECONCILED DEMO CONTROLS` means only that the synthetic control values match; production close still requires Controller-approved GL tie-out and cutoff treatment.
4. **What is not built?** Amazon SP-API authentication, live ERP integration, scheduler/retries, multi-currency/tax handling, real historical settlement backfills, permission model, and production-grade monitoring. These are design/implementation follow-ups.
5. **Why not use an off-the-shelf connector?** I would use a maintained connector where appropriate. My differentiated work is the finance schema, reconciliation logic, controlled exceptions, and decision-ready evidence.

**Honest attribution:** the software was developed with AI coding assistance. I own the financial definitions, design choices, test cases, explanation, and ability to modify, debug, and evaluate the code. Practice each edit until that claim is true in a timed exercise.
