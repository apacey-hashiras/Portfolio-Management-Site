Below is a single, focused, implementation-ready **Option A** specification (Markdown) — the **“Companies = Investments”** simplified model you requested.
Give this to an AI website-builder agent or a dev team: it contains the **Postgres DDL**, **computed-field definitions**, **waterfall & XIRR algorithms**, **REST API**, **frontend + UX**, **jobs/materialized view guidance**, and **acceptance tests**. It’s tailored to be fast to implement while supporting correct accounting (chronological waterfall, IRR, fees, carry).

---

# Fund Portfolio Platform — Option A: *Companies = Investments*

> **Design principle**: each row in `portfolio_companies` is the fund’s *investment* record. Use `transactions` for dated cash movement (capital calls, fees, distributions). This keeps the model simple but correct for fund return calculations.

---

## 1 — Goals

* Model funds and portfolio investments (one company row = one investment).
* Track dynamic fields (rounds, allocation, dates, valuations, rounds raised, exits).
* Track fixed fund-level inputs (fund start date, management fee %, carry %, tenure).
* Compute fund returns correctly: chronological waterfall (ROC → profits split), LP & GP splits, Gross/Net MOIC, DPI, TVPI, Gross/Net IRR.
* Provide APIs, front-end pages, and exports.

---

## 2 — Technology recommendations

* **DB**: PostgreSQL (relational + JSONB flexibility).
* **Backend**: Python (FastAPI) or Node.js (Express/Fastify). Use a numeric library for XIRR (Python `numpy_financial.xirr` or `pyxirr`; Node `xirr` packages).
* **Frontend**: React + a charting library (Recharts / Highcharts).
* **Jobs/Cache**: Redis queue for background recomputations and caching.
* **Storage**: S3-compatible for exports.
* **Auth**: OAuth2 / RBAC.

---

## 3 — Database schema (Option A)

### 3.1 `funds`

```sql
CREATE TABLE funds (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name              TEXT NOT NULL,
  fund_code         TEXT,
  manager_id        UUID, -- references users.id if auth used
  fund_start_date   DATE NOT NULL,
  fund_tenor_years  INTEGER NOT NULL DEFAULT 10,
  total_commitment  NUMERIC(20,2) NOT NULL,
  management_fee_pct NUMERIC(5,4) NOT NULL, -- 0.005 => 0.5%
  carry_pct         NUMERIC(5,4) NOT NULL, -- 0.35 => 35%
  investment_period_years INTEGER DEFAULT 5,
  fee_calc_method   TEXT DEFAULT 'committed', -- committed|called|nav
  created_at        TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at        TIMESTAMP WITH TIME ZONE DEFAULT now(),
  metadata          JSONB DEFAULT '{}'
);

CREATE INDEX idx_funds_code ON funds(fund_code);
```

### 3.2 `portfolio_companies` (one row = fund’s investment)

```sql
CREATE TABLE portfolio_companies (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fund_id         UUID NOT NULL REFERENCES funds(id),
  name            TEXT NOT NULL,
  stage           TEXT, -- seed / series_a etc.
  country         TEXT,
  industry        TEXT,
  initial_investment_amount NUMERIC(20,2) NOT NULL DEFAULT 0,
  initial_investment_date   DATE,
  follow_on_reserved_amount NUMERIC(20,2) NOT NULL DEFAULT 0,
  is_follow_on_used BOOLEAN DEFAULT FALSE,
  total_invested NUMERIC(20,2) NOT NULL DEFAULT 0, -- initial + drawn follow-ons
  ownership_pct  NUMERIC(8,6), -- optional, decimal
  latest_post_money NUMERIC(20,2), -- optional, last known post-money valuation
  last_round_date DATE,
  status         TEXT DEFAULT 'active', -- active|exit|writeoff
  exit_date      DATE,
  exit_proceeds  NUMERIC(20,2) DEFAULT 0, -- gross amount the fund received
  description    TEXT,
  metadata       JSONB DEFAULT '{}',
  created_at     TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at     TIMESTAMP WITH TIME ZONE DEFAULT now(),
  UNIQUE (fund_id, name)
);

CREATE INDEX idx_pc_fund ON portfolio_companies(fund_id);
```

### 3.3 `transactions` (cashflow timeline)

```sql
CREATE TYPE tx_type AS ENUM ('capital_call','management_fee','other_fee','distribution','carry_payment','other');

CREATE TABLE transactions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fund_id       UUID NOT NULL REFERENCES funds(id),
  company_id    UUID REFERENCES portfolio_companies(id), -- optional
  transaction_date DATE NOT NULL,
  amount        NUMERIC(20,2) NOT NULL, -- positive value; sign inferred from tx_type
  tx_type       tx_type NOT NULL,
  reference     TEXT,
  related_id    UUID, -- optional link (e.g., invoice id)
  created_by    UUID,
  created_at    TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at    TIMESTAMP WITH TIME ZONE DEFAULT now(),
  metadata      JSONB DEFAULT '{}'
);

CREATE INDEX idx_tx_fund_date ON transactions(fund_id, transaction_date);
CREATE INDEX idx_tx_company ON transactions(company_id);
```

**Sign convention**: `amount` is **positive**. Interpret as:

* `capital_call`, `management_fee`, `other_fee` → treated as **outflow** when building IRR (-amount).
* `distribution`, `carry_payment` → treated as **inflow** (+amount).

### 3.4 `waterfall_allocations` (materialized results)

```sql
CREATE TABLE waterfall_allocations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fund_id UUID REFERENCES funds(id),
  transaction_id UUID REFERENCES transactions(id),
  distribution_date DATE,
  gross NUMERIC(20,2),
  roc_paid NUMERIC(20,2),
  profit_portion NUMERIC(20,2),
  lp_share NUMERIC(20,2),
  gp_share NUMERIC(20,2),
  lp_distribution NUMERIC(20,2),
  gp_distribution NUMERIC(20,2),
  remaining_capital_to_return NUMERIC(20,2),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_wf_fund ON waterfall_allocations(fund_id);
CREATE INDEX idx_wf_tx ON waterfall_allocations(transaction_id);
```

---

## 4 — Key computed values (Fields & queries)

> Implement these either as materialized views (recommended) or compute on demand in the backend.

### 4.1 Company-level

* `company.total_invested` — stored field. Keep in sync on writes.
* `company.unrealized_value` — optional; prefer `latest_post_money * ownership_pct` or a manual `company_marked_value` in `metadata`.
* `company.realized_proceeds = exit_proceeds` (stored).

### 4.2 Fund-level core metrics

Compute (SQL snippets):

* **Total Contributed (Called)**
  `fund_total_contributed = COALESCE(SUM(pc.total_invested),0)`
  or (if preferring transaction-based):
  `SUM(CASE WHEN tx.tx_type='capital_call' THEN tx.amount ELSE 0 END)`

* **Total Distributions (gross)**
  `fund_total_distributions = SUM(CASE WHEN tx.tx_type='distribution' THEN tx.amount ELSE 0 END)`

* **Total Fees Paid**
  `fund_total_fees = SUM(CASE WHEN tx.tx_type IN ('management_fee','other_fee') THEN tx.amount ELSE 0 END)`

* **Fund Unrealized Value**
  `SUM(COALESCE(pc.latest_post_money * pc.ownership_pct, 0))`
  *(or use a separate `company_marked_value` field to store NAV directly)*

* **Gross MOIC** = `fund_total_distributions / fund_total_contributed` (handle zero)

* **LP Net TVPI** = `(LP_total_distributions + fund_unrealized_value) / fund_total_contributed`

  * `LP_total_distributions` = `SUM(lp_distribution from waterfall_allocations OR compute from distributions - GP carry)`

* **DPI (Net)** = `LP_total_distributions / fund_total_contributed`

* **GP Carry (total)** = `SUM(gp_distribution from waterfall_allocations)`

### 4.3 IRR

* Build date series of cashflows for LP:

  * For each capital call transaction → cashflow `=-amount` on transaction_date
  * For each management_fee transaction → cashflow `=-amount` on transaction_date
  * For each distribution transaction → cashflow `=+lp_distribution` on transaction_date (lp share after waterfall)
* Compute `XIRR(cashflows, dates)` using a numeric library (Python `numpy_financial.xirr` or Node `xirr`). Do **not** use SQL-only IRR in Postgres for precision and edge cases.

---

## 5 — Waterfall algorithm (chronological) — exact process

**Assumptions**:

* `Total_Contributed = SUM(portfolio_companies.total_invested)` (sum of *actual* invested amounts).
* Carry is `carry_pct` (e.g., 35% from fund metadata).
* Waterfall rule: **Return of Capital (ROC)** first; then **profits split**: LP gets `(1 - carry_pct)` of profits; GP gets `carry_pct`.

**Pseudocode (run by backend job on `distribution` transactions ordered by date):**

```pseudo
remaining_capital_to_return = Total_Contributed
for distribution IN distributions ORDER BY transaction_date ASC:
    gross = distribution.amount  # gross cash received by fund at this date

    roc_paid = MIN(remaining_capital_to_return, gross)
    remaining_capital_to_return -= roc_paid
    profit_portion = gross - roc_paid

    gp_share = ROUND(profit_portion * carry_pct, 2)
    lp_share_profit = profit_portion - gp_share

    lp_distribution = roc_paid + lp_share_profit
    gp_distribution = gp_share

    INSERT INTO waterfall_allocations(...) values (... computed fields ...)

# After loop, totals:
total_lp_distributions = SUM(lp_distribution)
total_gp_carry = SUM(gp_distribution)
```

**Notes**:

* Round monetary values to cents (2 decimals).
* This algorithm *implements exactly* “Return of capital; Then profits and carry.” No hurdle or catch-up. If you later need an 8% preferred return or GP catch-up, add logic before profit split.

---

## 6 — Materialized views & background jobs

**Materialized views to build & refresh**:

1. `mv_fund_aggregates(fund_id, as_of_date, total_contributed, total_distributions, total_fees, fund_unrealized_value, gross_moic)` — refresh nightly & after writes.
2. `mv_company_aggregates` — per `portfolio_companies` derived metrics.
3. `mv_waterfall_latest` — latest `waterfall_allocations` per fund.

**Background jobs**:

* **Waterfall Job**: whenever a `transactions` row of `tx_type='distribution'` is inserted/updated/deleted for a fund, enqueue job to recompute waterfall for that fund (reads `Total_Contributed` and ordered distributions). Use idempotent job that replaces `waterfall_allocations` for that fund.
* **Aggregates Job**: recompute `mv_fund_aggregates` after waterfall job completes.

**Triggers**:

* Use DB triggers to enqueue jobs on insert/update/delete of `transactions` or updates to `portfolio_companies.total_invested`. Prefer application-level eventing to keep DB simple.

---

## 7 — REST API (Option A): essential endpoints

> All endpoints require auth. Use standard pagination & filters.

### Funds

* `GET /api/funds` — list funds
* `POST /api/funds` — create fund
* `GET /api/funds/:id` — get fund + aggregated metrics (call mv_fund_aggregates)
* `PUT /api/funds/:id` — update fund

**Create payload example**:

```json
{
  "name": "Hashiras: Yoriichi I",
  "fund_code": "YORIICHI-I",
  "fund_start_date": "2026-04-01",
  "total_commitment": 100000000,
  "management_fee_pct": 0.005,
  "carry_pct": 0.35,
  "investment_period_years": 5
}
```

### Portfolio Companies (investments)

* `GET /api/funds/:fund_id/companies` — list investments
* `POST /api/funds/:fund_id/companies` — create investment (company = investment)
* `GET /api/companies/:company_id` — details
* `PUT /api/companies/:company_id` — update

**Create (investment) payload**:

```json
{
  "name": "Alia",
  "stage": "pre-seed",
  "initial_investment_amount": 1250000,
  "initial_investment_date": "2026-04-01",
  "follow_on_reserved_amount": 17000000,
  "total_invested": 18250000,
  "ownership_pct": 0.025,
  "latest_post_money": 50000000,
  "metadata": {"founder":"Thomas Filshill"}
}
```

### Transactions

* `GET /api/funds/:fund_id/transactions`
* `POST /api/funds/:fund_id/transactions` — create capital calls, fees, distributions
* `GET /api/transactions/:id` — get tx

**Distribution payload example**:

```json
{
  "transaction_date": "2032-03-12",
  "amount": 182500000,
  "tx_type": "distribution",
  "company_id": "<company_uuid>",
  "reference": "Exit sale"
}
```

**Capital call payload example**:

```json
{
  "transaction_date": "2027-05-01",
  "amount": 5000000,
  "tx_type": "capital_call",
  "company_id": "<company_uuid>",
  "reference": "Follow-on tranche 1"
}
```

### Metrics & Waterfall

* `GET /api/funds/:fund_id/metrics` — returns aggregated fund metrics + IRR (invoke mv_fund_aggregates and compute XIRR)
* `GET /api/funds/:fund_id/waterfall` — returns `waterfall_allocations` rows
* `GET /api/companies/:company_id/metrics` — company MOIC / invested / unrealized / exit proceeds

**Metrics response sample**:

```json
{
  "fund_id": "uuid",
  "total_contributed": 95000000,
  "total_distributions": 680250000,
  "total_fees": 5000000,
  "gross_moic": 7.163,
  "lp_net_moic": 4.7716,
  "funnd_gross_irr": 0.680, -- optional
  "fund_net_irr": 0.4245,
  "total_gp_carry": 203087500
}
```

---

## 8 — Frontend & UX (minimum viable)

1. **Fund Dashboard**

   * KPIs: Fund size, start date, tenor, management fee %, carry %, Total Contributed, Total Distributions, Gross MOIC, Net TVPI, DPI, Net IRR, GP Carry.
   * Time series: cumulative capital calls vs distributions (stacked line/area).
   * Waterfall chart: stacked bars per distribution (ROC / Profit → LP/GP split).

2. **Investments list (Companies-as-Investments)**

   * Table: Company, Stage, Initial Investment, Follow-on Reserved, Total Invested, Ownership %, Latest Post-Money, Status, Exit Proceeds, MOIC (if realized).
   * Row actions: Edit, Add Transaction, Mark Exit.

3. **Investment detail**

   * Show meta, investment amounts, timeline (transactions tied to this company), cap table fields, and documents.

4. **Transactions page**

   * List with filters (by company, tx_type, date). Add new transactions via form.

5. **Waterfall page**

   * Chronological table + stacked bar chart per distribution with toggles to see LP vs GP share, and cumulative ROC remaining.

6. **Exports**

   * Export CSV/XLSX of fund metrics, waterfall allocations, investment list.

---

## 9 — Data validation & business rules

* `total_invested` must equal `initial_investment_amount + sum(drawn_follow_ons)`; update on transactions or API writes.
* On `POST /transactions` with `tx_type='capital_call'` and `company_id` present: backend increments `portfolio_companies.total_invested` by `amount`, and if `amount` uses `follow_on_reserved_amount`, mark `is_follow_on_used=true` when fully drawn.
* `exit_proceeds` should be set on exit & a `distribution` transaction recorded at the same date. Keep `portfolio_companies.status='exit'` and `exit_date`.
* No hard delete of transactions; use soft delete flag + audit log.

---

## 10 — XIRR & numeric considerations

* **XIRR**: compute on backend with reliable library. Provide fallback with Newton-Raphson solver if necessary.
* **Numeric precision**: use NUMERIC(20,2) in Postgres, round to 2 decimals for monetary outputs. Use decimal arithmetic in backend to avoid floating point rounding errors.

**Python XIRR snippet**:

```python
import numpy_financial as nf
# cashflows: [-1000000, 0, 1200000], dates: [date1, date2, date3]
irr = nf.xirr(cashflows, dates)  # returns annualized IRR (float)
```

---

## 11 — Acceptance tests / QA

1. **Seed Hashiras example**:

   * Load fund: `total_commitment = 100,000,000`, `management_fee_pct=0.005`, `carry_pct=0.35`.
   * Create 8 investments matching example (A–H) with `total_invested` totals and `exit_proceeds` as described earlier.
   * Create `transactions` for capital calls (initial + follow-ons) and for distributions (exits). Run waterfall job.
   * Expected aggregates (example): `total_contributed = 95,000,000`, `total_distributions = 680,250,000`, `GP_carry ≈ 203,087,500`, `LP_net_moic ≈ 4.77`, `LP_net_irr ≈ 42%` (approx). Tolerances allowed for rounding.

2. **Waterfall chronology**: add distributions in different orders; waterfall allocations must change accordingly (ROC is paid out first). Validate sums: `SUM(lp_distribution + gp_distribution) == SUM(gross_distributions)`.

3. **XIRR validation**: compute IRR with an external tool (Excel/XIRR) to confirm platform results.

4. **CRUD tests**: create/update/delete (soft) funds, companies, transactions; ensure aggregate refresh and waterfall recompute.

---

## 12 — CSV import / sample schema for fast onboarding

**Investments CSV (columns)**:
`fund_code,name,stage,initial_investment_amount,initial_investment_date,follow_on_reserved_amount,total_invested,ownership_pct,latest_post_money,status`

**Transactions CSV**:
`fund_code,company_name,transaction_date,amount,tx_type,reference`

When importing:

* Match `fund_code` and `company_name` to existing rows; create missing companies.
* Validate dates and amounts. Queue waterfall & aggregate recompute after import.

---

## 13 — Security & roles

* Roles: `admin`, `fund_manager`, `gp`, `lp`, `viewer`.
* `fund_manager` can edit fund, companies, transactions. `lp` can view metrics and exports. `viewer` read-only. `admin` manages users.
* Audit log for all writes: who/when/what changed.
* TLS, RBAC, secrets manager for DB creds.

---

## 14 — Next steps for an AI builder or dev team

1. Implement DDL above in Postgres.
2. Implement backend routes & controller logic for funds, portfolio_companies, transactions.
3. Implement waterfall job: recompute `waterfall_allocations` for fund when any distribution transaction changes.
4. Implement materialized views and background job scheduling.
5. Build frontend components and wire to endpoints.
6. Seed the Hashiras example and validate acceptance tests.

---

## 15 — Example mapping for Hashiras (quick)

**Fund**:

* `name`: `Hashiras: Yoriichi I`
* `fund_start_date`: `2026-04-01`
* `total_commitment`: `100000000`
* `management_fee_pct`: `0.005`
* `carry_pct`: `0.35`
* `investment_period_years`: `5`

**Investments** (illustrative): companies A–E `total_invested=18,250,000` each; F–H `total_invested=1,250,000` each; total_contributed = 95,000,000.

Record capital calls as `transactions` (dates for initial and follow-ons) and the exits as `distribution` transactions. Run waterfall algorithm to produce `waterfall_allocations` and compute LP & GP distributions and IRR.

---