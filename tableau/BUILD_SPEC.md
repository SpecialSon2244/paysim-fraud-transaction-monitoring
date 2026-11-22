# Tableau Public build spec

How to build one dashboard in Tableau Public web authoring from `paysim_fraud_monitoring.xlsx`.
Every chart uses one sheet of that file as it is. No joins and no calculated fields are needed.
Build it in small steps: one data source, one sheet, save, then the next.

Facts about the file:

- Size: about 16 KB, 10 sheets, at most 31 rows each. No size issue.
- All percentages are stored as numbers from 0 to 100 (77.71 means 77.71%). Do not use Tableau's
  "Percentage" format, it would show 7771%.
- Data: PaySim synthetic transactions, 6,362,620 rows, 31 days (1 step = 1 hour). Synthetic, no real customers.
- The `about` sheet holds notes only. Do not chart it.

## Colours

| Value | Hex | Used in |
|---|---|---|
| Family = Chain | `#2A9D8F` (teal) | Sheet 2 |
| Family = Amount | `#F4A261` (orange) | Sheet 2 |
| Family = Velocity | `#E9C46A` (sand) | Sheet 2 |
| Family = Timing | `#264653` (navy) | Sheet 2 |
| Family = Balance (leaky) | `#CED4DA` (light grey) | Sheet 2 |
| Family = Baseline | `#E76F51` (coral) | Sheet 2 |
| Fraud / Has fraud | `#E76F51` (coral) | Sheets 3, 4, 6 |
| Not fraud / No fraud / all transactions | `#CED4DA` (light grey) | Sheets 3, 4, 6 |
| Recall % | `#2A9D8F` (teal) | Sheet 5 |
| Precision % | `#E76F51` (coral) | Sheet 5 |

How to set them: Color legend menu, Edit Colors, click a value, type or pick the colour. If the web editor offers
no hex input, pick the closest swatch and note which one was used.

## Number formats

| Field | Format |
|---|---|
| Any "%" field | Number (Custom), 2 decimals, suffix `%` |
| Alerts, Fraud caught, False alarms, Transactions, Fraud | Number (Custom), 0 decimals, thousands separator on |
| Alerts per day | Number (Custom), 1 decimal, thousands separator on |
| Value (kpi sheet) | Number (Custom), 2 decimals is fine; the labels below say which are counts |

## Step 0. Connect the data

1. Sign in to public.tableau.com, My Profile, Create, Web Authoring.
2. Connect to Data, Files, upload `paysim_fraud_monitoring.xlsx`.
3. Drag `kpi` onto the canvas. Rename the data source (top left) to `kpi`.
4. For each other sheet used below: Data pane, New Data Source, upload the same file again, drag only that sheet,
   rename the data source to the sheet name. You end with 6 data sources:
   `kpi`, `rules`, `by_type`, `by_hour`, `budget`, `leakage`.
5. Do not join or relate the sheets. They have different grains.

Field roles to check (field menu, Convert to Dimension / Discrete if Tableau guessed wrong):

- Text fields (Metric, Rule, Family, Leakage, Type, Fraud present, Window, Check, Label) are dimensions.
- `Hour` (by_hour) and `Alerts per day budget` (budget) must be **dimensions, discrete**, so they show as a
  category axis. `Order` (kpi) is only for sorting.

Each sheet has one row per mark, so SUM() of a percentage just returns the stored value. Keep SUM.

## Sheets

### Sheet 1. KPI strip

- Data source: `kpi`
- Filter: Metric, keep only "Transactions", "Fraud transactions", "isFlaggedFraud recall %",
  "Chain rule R07 recall %", "Chain rule R07 precision %"
- Columns: Metric (sort by field Order, ascending)
- Marks: Text. Text: SUM(Value)
- Format the text 20 pt bold, Metric header 11 pt grey. Hide the row/column dividers.
- Expected values: 6,362,620 · 8,213 · 0.19 · 99.27 · 77.71
- Title: hide

### Sheet 2. Rule scorecard (scatter)

- Data source: `rules`
- Columns: SUM(Alerts per day). Axis: Edit Axis, Scale: Logarithmic, title "Alerts per day (log scale)"
- Rows: SUM(Recall %). Axis fixed 0 to 105, title "Recall: share of fraud caught (%)"
- Detail: Rule
- Marks: Circle, size about 40%
- Color: Family (colours above)
- Shape (optional): Leakage, "Leaky" = diamond, "Usable" = circle
- Label: Rule and SUM(Precision %), e.g. "R07 TRANSFER then CASH_OUT chain 77.71%". Label font 9 pt.
  If labels overlap, set Label, Marks to Label: "Selected" for the crowded ones (R02, R03, R05).
- Tooltip: Rule, Definition, Alerts, Fraud caught, Precision %, Recall %, Alerts per day, Leakage
- Title: "The chain rule catches 99.27% of fraud at 338 alerts a day; the built-in flag catches 0.19%"

### Sheet 3. Fraud by type

- Data source: `by_type`
- Columns: Type, sorted by SUM(Fraud) descending
- Rows: SUM(Fraud)
- Marks: Bar. Color: Fraud present ("Has fraud" coral, "No fraud" grey). Label: SUM(Fraud)
- Tooltip: Type, Transactions, Fraud, Fraud rate %, isFlaggedFraud
- Title: "All fraud is TRANSFER (4,097) or CASH_OUT (4,116)"

### Sheet 4. Fraud by hour of day

- Data source: `by_hour`
- Columns: Hour (discrete dimension, 0 to 23)
- Rows: SUM(Transactions) and SUM(Fraud) → right-click the second pill, Dual Axis
- Marks card SUM(Transactions): Bar, colour light grey `#CED4DA`
- Marks card SUM(Fraud): Line, colour coral `#E76F51`, markers on
- Do **not** synchronise the axes (very different scales). Right axis title "Fraud transactions", left
  "All transactions"
- Optional: Color the bars by Window ("Night 0-5" navy at 30% opacity, "Day 6-23" grey)
- Tooltip: Hour, Transactions, Fraud, Fraud rate %
- Title: "Fraud is flat (274 to 375 per hour); normal traffic drops to 1,241 at hour 4"

### Sheet 5. Alert budget

- Data source: `budget`
- Columns: Alerts per day budget (discrete dimension; values 25 to 2000 in order)
- Rows: Measure Values, with Measure Names filter = Recall %, Precision % only
- Marks: Line, markers on. Color: Measure Names (Recall teal, Precision coral)
- Axis fixed 0 to 105, title "%". Label: on at the 300 column only (or all, 1 decimal)
- Tooltip: Alerts per day budget, Recall %, Precision %, Alerts, Fraud caught
- Title: "Reviewing 300 alerts a day catches 96.3% of fraud at 85.24% precision"

### Sheet 6. Leakage check

- Data source: `leakage`
- Rows: Check, then Label
- Columns: SUM(Share %), axis fixed 0 to 110
- Marks: Bar. Color: Label (Fraud coral, Not fraud grey). Label: SUM(Share %), 2 decimals
- Title: "Balance rules are leaky: 97.82% of fraud rows move the whole balance, 0.00% of normal rows"

## Dashboard: "Which monitoring rules are worth an analyst's time?"

- Size: Fixed, 1200 x 900.
- Use **floating** objects with these typed positions (Layout pane, Position x/y and Size w/h, in pixels):

| Object | x | y | w | h | Notes |
|---|---:|---:|---:|---:|---|
| Text: title | 0 | 0 | 1200 | 50 | "Which monitoring rules are worth an analyst's time?" Bold, 22 pt |
| Text: credit | 0 | 50 | 1200 | 40 | 10 pt grey: "PaySim synthetic mobile-money transactions (Lopez-Rojas et al. 2016), Kaggle ealaxi/paysim1, CC BY-SA 4.0. 6,362,620 transactions, 31 days. Synthetic data: no real customers." |
| Sheet 1 KPI strip | 0 | 90 | 1200 | 90 | title hidden |
| Sheet 2 Rule scorecard | 0 | 180 | 700 | 400 | Family legend inside, top right of the plot (x 560, y 190, w 130, h 140, floating) |
| Sheet 5 Alert budget | 700 | 180 | 500 | 400 | Measure Names legend under the title |
| Sheet 3 Fraud by type | 0 | 580 | 400 | 320 | hide its colour legend |
| Sheet 4 Fraud by hour | 400 | 580 | 450 | 320 | |
| Sheet 6 Leakage check | 850 | 580 | 350 | 320 | Label legend hidden (the title explains the colours) |

- Remove any legends Tableau adds automatically except the two noted above.
- Dashboard actions: none needed.

## Before publishing

- Check the numbers in the titles against `docs/findings.json` and `exports/rule_metrics.csv`.
- Workbook name: "PaySim transaction monitoring: which rules to keep".
- Publish to Tableau Public only when Abhiram has looked at it.
- After publishing, paste the public link into the Dashboard section of `README.md`.
