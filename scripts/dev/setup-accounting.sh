#!/usr/bin/env bash
# Wire up the Odoo Mates accounting suite for a company (idempotent):
#   - Fiscal Year for the given year (default: current year per the container)
#   - Accumulated Depreciation account (contra-asset)
#   - "General Assets" asset category (Fixed Asset / Accum. Dep. / Expense / MISC)
#
#   scripts/dev/setup-accounting.sh <db> [YEAR]
set -euo pipefail
cd "$(dirname "$0")/../.."

DB="${1:-}"
[ -n "$DB" ] || { echo "Usage: scripts/dev/setup-accounting.sh <db> [YEAR]"; exit 1; }
export AFR_YEAR="${2:-}"

docker compose run --rm --no-deps -T -e AFR_YEAR web odoo shell -d "$DB" --no-http <<'PY'
import os
from datetime import date
company = env.ref('base.main_company')
year = int(os.environ.get('AFR_YEAR') or date.today().year)

# --- Fiscal Year (only if om_fiscal_year is installed) ---
if 'account.fiscal.year' in env:
    FY = env['account.fiscal.year']
    if not FY.search([('company_id','=',company.id),('date_from','=','%d-01-01' % year)], limit=1):
        FY.create({'name': str(year), 'date_from': '%d-01-01' % year,
                   'date_to': '%d-12-31' % year, 'company_id': company.id})
        print('  fiscal year %d created' % year)
    else:
        print('  fiscal year %d exists' % year)
else:
    print('  fiscal year: skipped (om_fiscal_year not installed)')

# --- Accumulated Depreciation account ---
AA = env['account.account']
acc_dep = AA.search(['|', ('code','=','151100'),
                     ('name','ilike','accumulated depreciation')], limit=1)
if not acc_dep:
    vals = {'code':'151100','name':'Accumulated Depreciation','account_type':'asset_fixed'}
    if 'company_ids' in AA._fields:
        vals['company_ids'] = [(6,0,[company.id])]
    elif 'company_id' in AA._fields:
        vals['company_id'] = company.id
    acc_dep = AA.create(vals)
    print('  accumulated depreciation account 151100 created')

# --- Asset category (only if om_account_asset is installed) ---
if 'account.asset.category' in env:
    exp = AA.search([('account_type','like','expense')], limit=1)
    fixed = (AA.search([('account_type','=','asset_fixed'),('code','!=','151100')], limit=1)
             or AA.search([('account_type','like','asset')], limit=1))
    journal = env['account.journal'].search([('type','=','general')], limit=1)
    Cat = env['account.asset.category']
    cat = Cat.search([('name','=','General Assets')], limit=1)
    cvals = {'account_asset_id': fixed.id, 'account_depreciation_id': acc_dep.id,
             'account_depreciation_expense_id': exp.id, 'journal_id': journal.id,
             'method_number': 5, 'method_period': 12}
    if cat:
        cat.write(cvals)
        print('  asset category "General Assets" updated')
    elif exp and fixed and journal:
        cvals['name'] = 'General Assets'
        Cat.create(cvals)
        print('  asset category "General Assets" created')
else:
    print('  asset category: skipped (om_account_asset not installed)')
env.cr.commit()
print('  done.')
PY
