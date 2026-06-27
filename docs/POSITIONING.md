# Community Plus ERP — Sales & Positioning Sheet

> **Run every team in your business on one platform — free of per-user license fees.**
> Built on Odoo 19 Community + audited open-source + our own clean-room modules.
> No Enterprise subscription. Unlimited users. Self-hosted or cloud.

---

## The pitch (30 seconds)

Most SMEs are quoted **$25–40 per user, per month** for a full ERP. Community Plus
delivers the same day-to-day capability — Sales, Finance, HR, Marketing, Operations,
Services, Support — with **no per-user fee**. You pay for hosting and setup, not for
seats. Add 5 users or 500: the software cost doesn't change.

---

## What it runs — by team

| Team | Value delivered | Headline apps |
|---|---|---|
| **Sales** | Lead-to-cash, recurring revenue, in-store & online | CRM · Sales · Subscriptions · POS · eCommerce · Loyalty |
| **Finance** | Books, reporting, tax, assets, cash visibility | Accounting · Invoicing · Cash Flow · Loans · Budgets · Overview dashboard |
| **HR** | Hire-to-retire, payroll, scheduling | Employees · Payroll · Recruitment · Time Off · Appraisals · Planning · Referrals |
| **Marketing** | Reach, automate, measure | Email · SMS · Marketing Automation · Social · Events · Surveys |
| **Operations** | Stock, buy, make, inspect | Inventory · Purchase · Manufacturing · Quality · Maintenance · Barcode |
| **Services** | Deliver work, bill time, support on-site | Project · Timesheets · Field Service · Appointments · Helpdesk |
| **Support** | Tickets, chat, self-serve knowledge | Helpdesk · Live Chat · Knowledge |
| **IT / Admin** | Documents, signatures, approvals, control | Documents · Sign · Approvals · OCR · Settings |
| **Management** | One view of the whole business | Company Dashboard · Accounting Overview · MIS reports |
| **Comms** | Talk, meet, schedule | Discuss · Calendar · Meeting Rooms · Phone · WhatsApp · AI |

**60+ apps. 10 teams. One platform.**

---

## What's included vs. add-on

**✅ Included (free, no external account):**
all of the above — accounting, CRM, sales, HR, payroll, inventory, manufacturing,
marketing, projects, helpdesk, documents, e-sign, dashboards, **invoice OCR**
(free Tesseract), **barcode** (USB scanners), **click-to-call**, dark mode.

**🔌 Add-on (works once you connect your own account/keys):**

| Feature | What you provide |
|---|---|
| Live bank-feed sync | A bank-aggregator subscription (Ponto / Qonto / Plaid) |
| AI assistant (live) | A free local LLM (Ollama) **or** an OpenAI / Anthropic key |
| WhatsApp / Social posting | Your Meta / X / LinkedIn API tokens |
| VoIP voice calls | A SIP telephony provider |

> The connectors are **built in** — they just need your credentials. No extra dev work.

**🚫 Not offered (be honest with prospects):**
deep manufacturing **Shop-Floor MES**, **Amazon** marketplace sync. Clients who require
these should license Odoo Enterprise for those specific modules.

---

## Community Plus vs. Enterprise

| | Community Plus | Odoo Enterprise |
|---|---|---|
| Per-user fee | **None** | ~$25–40 / user / month |
| Users | **Unlimited** | Per seat |
| Source | Open-source + our LGPL code | Proprietary |
| Hosting | Your server / cloud (you control) | Odoo cloud or self |
| Apps | 60+ (this sheet) | ~80 |
| Live bank sync / OCR AI / Studio | Add-on or alternative | Built-in (paid) |

**Sweet spot:** SMEs with **many users**, tight software budgets, and a need to **own
their data and deployment**.

---

## How clients get it (delivery)

One command provisions a fully-loaded, branded client instance:

```
make onboard db=<client> cc=<country> company="<Legal Name>" --seed
```

Every delivery is gated by an automated install test (`make pack-test`) and a
[delivery checklist](DELIVERY_CHECKLIST.md). Production deploy is multi-tenant with
wildcard HTTPS — see [DEPLOYMENT.md](DEPLOYMENT.md). Per-app source labels (Community /
open-source / custom) are tracked in [FEATURE_MATRIX.md](FEATURE_MATRIX.md).

## Licensing promise

100% license-clean. Every shipped module is **Native Community**, **audited open-source
(pinned)**, or **our own clean-room code** — never copied Enterprise source. Sell with
confidence.
