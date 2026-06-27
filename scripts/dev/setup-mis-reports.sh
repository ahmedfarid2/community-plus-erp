#!/usr/bin/env bash
# Create ready-made MIS Builder templates (Profit & Loss, Balance Sheet) using
# account_type domains so they work with any chart. Idempotent (by report name).
#   scripts/dev/setup-mis-reports.sh <db>
set -euo pipefail
cd "$(dirname "$0")/../.."
DB="${1:-}"
[ -n "$DB" ] || { echo "Usage: scripts/dev/setup-mis-reports.sh <db>"; exit 1; }

docker compose run --rm --no-deps -T web odoo shell -d "$DB" --no-http <<'PY'
if 'mis.report' not in env:
    print("mis_builder not installed — skipping.");
else:
    Report = env['mis.report']; KPI = env['mis.report.kpi']

    def ensure(name, kpis):
        rep = Report.search([('name', '=', name)], limit=1)
        if not rep:
            rep = Report.create({'name': name})
        rep.kpi_ids.unlink()
        for seq, (kname, desc, expr) in enumerate(kpis, start=1):
            KPI.create({'report_id': rep.id, 'name': kname, 'description': desc,
                        'expression': expr, 'sequence': seq * 10})
        return rep

    # --- Profit & Loss ---
    ensure('Profit & Loss', [
        ('revenue',   'Revenue',
         "-balp[('account_type','in',('income','income_other'))]"),
        ('expense',   'Expenses',
         "balp[('account_type','=like','expense%')]"),
        ('net_profit','Net Profit', "revenue - expense"),
    ])

    # --- Balance Sheet ---
    ensure('Balance Sheet', [
        ('assets',      'Assets',
         "bale[('account_type','=like','asset%')]"),
        ('liabilities', 'Liabilities',
         "-bale[('account_type','=like','liability%')]"),
        ('equity',      'Equity',
         "-bale[('account_type','in',('equity','equity_unaffected'))]"),
        ('liab_equity', 'Liabilities + Equity', "liabilities + equity"),
    ])

    # Ready-to-open instances for the current year.
    import datetime as _dt
    year = _dt.date.today().year
    Inst = env['mis.report.instance']; Per = env['mis.report.instance.period']
    for rname in ('Profit & Loss', 'Balance Sheet'):
        rep = Report.search([('name', '=', rname)], limit=1)
        iname = '%s %d' % (rname, year)
        if not Inst.search([('name', '=', iname)], limit=1):
            inst = Inst.create({'name': iname, 'report_id': rep.id})
            Per.create({'report_instance_id': inst.id, 'name': str(year), 'mode': 'fix',
                        'manual_date_from': '%d-01-01' % year,
                        'manual_date_to': '%d-12-31' % year, 'source': 'actuals'})

    env.cr.commit()
    print("MIS templates + %d instances ready:" % year,
          [r.name for r in Report.search([('name','in',('Profit & Loss','Balance Sheet'))])])
PY
