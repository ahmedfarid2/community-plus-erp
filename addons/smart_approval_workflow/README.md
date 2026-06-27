# Smart Approval Workflow (smart_approval_workflow)

> Create configurable approval workflows for any Odoo document.

A generic, reusable **approval engine** for Odoo Community. Define multi-level
approval flows for any model — purchase orders, vendor bills, expenses,
discounts, payments, inventory adjustments, refunds, HR requests, contracts, or
any custom model — without writing custom code for each client.

Replaces approvals done over WhatsApp / email / phone with a structured,
auditable process: clear steps, responsible approvers, approval history and a
real audit trail. The core depends only on `base` and `mail`; integrations ship
as separate optional modules.

## Models

| Model | Purpose |
|-------|---------|
| `approval.workflow` | A workflow for one document model, with an *applies-when* rule (always / amount-based / domain-based). |
| `approval.workflow.step` | A level in the workflow: approver (user / group / manager), required approvals, allow-reject. |
| `approval.request` | A request to approve a specific document; runs the state machine. |
| `approval.request.line` | One row per approval action — the audit trail. |
| `approval.action.wizard` | Captures the comment when approving / rejecting. |

## Install

```bash
docker compose run --rm --no-deps web odoo -d <db> -i smart_approval_workflow --stop-after-init
docker compose restart web
```

Then assign each user a group under **Settings → Users → Approvals**:
- **User** — create requests, act on requests assigned to them.
- **Manager** — view & act on all requests.
- **Administrator** — configure workflows and steps.

## Test the main flow

1. **Workflows → New** (as Administrator): pick a **Document Model**
   (e.g. *Contact*), set *Applies When = Always*, and add two steps —
   step 1 a specific user, step 2 a group. Save.
2. **Approval Requests → New**: choose the workflow, pick the **Document**,
   then **Submit for Approval**. The request becomes *Pending*, lands on step 1,
   and the step-1 approver gets a To-Do activity.
3. Log in as the step-1 approver → **My Pending Approvals** → open the request →
   **Approve** (add a comment). It advances to step 2.
4. As a step-2 group member → **Approve**. The request becomes *Approved*; the
   approved date and full history are recorded.
5. Try **Reject** at any step → request becomes *Rejected* with the reason stored.
   **Reset to Draft** lets you re-submit.

### Rules
- *Amount-based*: pick a numeric field and a minimum — the workflow applies (via
  the integration API) only when the document's amount meets the threshold.
- *Domain-based*: the document must match the domain (e.g. `[('is_company','=',True)]`).

## Extending it later (optional modules)

Each integration module `depends = ['smart_approval_workflow', <target>]` and
calls the public API to auto-create approvals — no core changes:

```python
# e.g. smart_approval_purchase: block confirming a PO until approved
def button_confirm(self):
    request = self.env['approval.request'].create_for_record(self)
    if request and request.state != 'approved':
        raise UserError(_("This purchase order needs approval first."))
    return super().button_confirm()
```

`create_for_record(record)` finds the matching active workflow (honouring its
amount / domain rule), creates the request and submits it. Planned modules:
`smart_approval_purchase`, `smart_approval_account`, `smart_approval_sale`,
`smart_approval_inventory`, `smart_approval_hr`, `smart_approval_payment_plan`
(e.g. require manager approval when a discount / waiver / payment delay exceeds a
limit).

## Design notes

- **Generic by construction** — the target document is `ir.model` + a `res_id`,
  surfaced as a clickable `Reference`. No industry terms, no hard-coded models.
- **Safe amount config** — the amount field is an `ir.model.fields` reference
  scoped to the chosen model, not a free-text string.
- **State machine** — `draft → pending → approved/rejected/cancelled`, advancing
  step by step; each step needs *N* approvals before moving on.
- **Audit trail** — every action is an `approval.request.line`; chatter and
  activities (`mail.thread` + `mail.activity.mixin`) track everything.
- **Guarded** — only resolved approvers (or an Administrator) can act, and only
  on pending requests; record rules scope visibility to owners/approvers.

## License

LGPL-3.
