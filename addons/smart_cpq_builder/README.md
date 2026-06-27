# Smart CPQ & Quotation Builder (smart_cpq_builder)

> Configure complex products, calculate prices automatically, and generate accurate quotations inside Odoo.

A generic **Configure-Price-Quote** engine for Odoo Community. Build configurable
products or service packages from option groups, options, pricing rules and
compatibility rules; validate selections; price each quote with a **safe** formula
evaluator; and track margins with a full calculation log. Industry-agnostic core
(`base` + `mail` + `product`).

## Models

| Model | Purpose |
|-------|---------|
| `cpq.template` | A configurable product/service template (base price, groups, rules). |
| `cpq.option.group` | A group of options (single/multiple, required, min/max). |
| `cpq.option` | One selectable option (fixed / % / formula price, cost). |
| `cpq.pricing.rule` | Sequenced dynamic price adjustment (condition → action). |
| `cpq.compatibility.rule` | requires / excludes / warning between two options. |
| `cpq.configuration` | A quote configuration: selections, prices, margin, state. |
| `cpq.configuration.line` | One selected option with its calculated price. |
| `cpq.calculation.log` | Per-rule pricing trace for transparency/debugging. |

## Install

```bash
docker compose run --rm --no-deps web odoo -d <db> -i smart_cpq_builder --stop-after-init
docker compose restart web
```
Assign users under **Settings → Users → CPQ**: User / Manager / Administrator.

## Test the main CPQ flow

1. **CPQ → Templates** (as Administrator): open *Aluminum Window (Demo)* — note the
   groups (Material, Glazing, Accessories, Installation), options, the bulk-discount
   pricing rule, and the "premium handles require premium aluminum" compatibility rule.
2. **CPQ → Configurations → New**: pick the template, set quantity, choose options.
3. **Recalculate Price** → the lines, totals, margin and calculation log update.
4. **Validate Configuration**:
   - Pick *Premium Handles* without *Premium Aluminum* → validation **blocks** with
     the compatibility message.
   - Add *Premium Aluminum* → validation passes; warnings (if any) are shown.
5. Set quantity above 10 → the bulk-discount rule fires (see the calculation log).

## How pricing works

For each configuration, `_recalculate()` runs deterministically:

1. **Options** — each selected option's unit price by `price_type`:
   `fixed` → amount, `percentage` → % of base price, `formula` → safe expression,
   `none` → 0. One `cpq.configuration.line` is created per option.
2. **Subtotal** — `(base_price + Σ option prices) × quantity`.
3. **Pricing rules** — applied in `sequence` order to a running total; each rule's
   condition is checked, then its action (`add_fixed`, `add_percentage`, `set_price`,
   `discount_fixed`, `discount_percentage`, `formula`) adjusts the total. Every step
   is recorded in `cpq.calculation.log` (before / delta / after).
4. **Discount & clamp** — the manual discount is subtracted; negative totals are
   clamped to 0 unless `ir.config_parameter` `cpq.allow_negative_price = 1`.
5. **Margins** — `cost_total` from option costs (+ optional base product cost) ×
   quantity; `margin_amount = total − cost`, `margin_percent` derived.

Recalculation runs automatically on create and whenever options, quantity,
discount, dimensions or template change, and via the **Recalculate Price** button.

## How compatibility validation works

`action_validate()` recalculates, then collects issues:

- **Required groups** must have a selection; **single** groups allow ≤ 1 option;
  **multiple** groups respect `min_selection` / `max_selection`.
- **Compatibility rules**: `requires` is violated when the source is selected but
  the target isn't; `excludes` / `warning` when both are selected. Each violation is
  raised at its `severity`: **blocking** prevents validation; **warning/info** are
  collected into `validation_message` without blocking.

Blocking issues raise a clear `UserError` listing everything that's wrong.

## Keeping formula evaluation safe

Formulas never use raw `eval`. They are evaluated with Odoo's
**`odoo.tools.safe_eval.safe_eval`** against a *controlled variable map* only:

```
base_price, quantity, width, height, length, area,
selected_options_count, selected_codes, current_total
```

`safe_eval` blocks builtins, imports, attribute access and dunder tricks. Any error
returns `0.0` / `False`, so a malformed admin formula degrades gracefully instead of
crashing a quote. To extend safely, add variables to `_formula_vars()` — never widen
the evaluator itself.

## Extending it later

Optional modules `depend = ['smart_cpq_builder', <target>]`:

- **smart_cpq_sale** — add `sale_order_id` + "Create Quotation" (one sale line with
  the configured price and the quote summary). Hooks reused: `_quote_description()`,
  `total_price`, `template_id.base_product_id`.
- **smart_cpq_mrp** — generate a BOM from selected options.
- **smart_cpq_website** — online product configurator.
- **smart_cpq_reports** — professional PDF quotations.
- **smart_cpq_ai** — summarize requirements / suggest configurations.
- **smart_cpq_import** — Excel import of templates and options.
- **smart_cpq_payment_plan** — build an installment plan from the quote total.
- **smart_cpq_approval_workflow** — require approval for low-margin / high-discount
  configurations (wire `margin_percent` / `discount_amount` to Smart Approval).

## License

LGPL-3.
