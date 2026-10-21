## Data in Redshift and who can see it (snapshot 2026-10-05)

Cluster `rsidc-cluster` (ap-east-1) → database **`dev`** → 3 user tables, 9 rows. The full data below was read as the admin (`rsadmin`), which bypasses RLS. Values that the matrix UPDATE cases modify (`budget`, `risk_score`) grow by +1 per matrix run.

**dev.marketing.campaigns**

| campaign_id | name | budget | status |
|---|---|---|---|
| 1 | Mid-Autumn Promo | 50004.00 | ACTIVE |
| 2 | Double 11 | 120000.00 | PLANNED |

**dev.risk.credit_limits**

| customer_email | credit_limit | risk_score |
|---|---|---|
| alice@cust.example | 10000.00 | 724 |
| carol@cust.example | 5000.00 | 640 |

**dev.sales.orders**

| order_id | region | customer_email | amount | order_date |
|---|---|---|---|---|
| 1 | APAC | alice@cust.example | 1200.00 | 2026-09-01 |
| 2 | APAC | bob@cust.example | 560.50 | 2026-09-03 |
| 3 | EMEA | carol@cust.example | 980.00 | 2026-09-05 |
| 4 | AMER | dave@cust.example | 2300.00 | 2026-09-07 |
| 5 | EMEA | erin@cust.example | 150.25 | 2026-09-09 |


### What each persona gets back (same SQL, run through the OBO agent as that user)

Regenerate with: `cd tests && ../infra/run.sh ../agent_obo/.venv/bin/python data_views.py && ../infra/run.sh ../agent_obo/.venv/bin/python render_data_views.py`

| Persona (IdC group) | Redshift session user | `SELECT * FROM marketing.campaigns` | `SELECT * FROM risk.credit_limits` | `SELECT * FROM sales.orders` |
|---|---|---|---|---|
| wei (risk-team) | `AWSIDC:wei@techfinance.example.com` | ✗ permission denied for schema marketing | 2/2 rows | 5/5 rows |
| zhang (marketing-team) | `AWSIDC:zhang@techfinance.example.com` | 2/2 rows | ✗ permission denied for schema risk | 2/5 rows, columns: order_id, region, amount, order_date (hidden: customer_email) |
| chen (platform-team) | `AWSIDC:chen@techfinance.example.com` | 2/2 rows | 2/2 rows | 5/5 rows |
| ds1 (data-scientists) | `AWSIDC:tojackywu@gmail.com` | ✗ permission denied for schema marketing | ✗ permission denied for schema risk | ✗ permission denied for schema sales |


**zhang: `SELECT * FROM sales.orders`** (RLS keeps only the APAC rows; the column grant **silently drops `customer_email`** from `SELECT *`; naming the column explicitly returns `42501 permission denied`)

| order_id | region | amount | order_date |
|---|---|---|---|
| 1 | APAC | 1200.00 | 2026-09-01 |
| 2 | APAC | 560.50 | 2026-09-03 |
