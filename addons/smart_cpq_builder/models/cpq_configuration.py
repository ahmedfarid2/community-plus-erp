from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class CpqConfiguration(models.Model):
    _name = "cpq.configuration"
    _description = "CPQ Configuration"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        index=True, default=lambda s: "New")
    template_id = fields.Many2one(
        "cpq.template", string="Template", required=True, tracking=True,
        domain="[('state','=','active')]")
    partner_id = fields.Many2one("res.partner", string="Customer", tracking=True)
    company_id = fields.Many2one(
        "res.company", default=lambda s: s.env.company, required=True)
    currency_id = fields.Many2one(
        "res.currency", required=True,
        default=lambda s: s.env.company.currency_id)
    user_id = fields.Many2one(
        "res.users", string="Salesperson", default=lambda s: s.env.user,
        tracking=True)
    quantity = fields.Float(default=1.0, required=True)

    # Optional dimension inputs available to formulas.
    width = fields.Float()
    height = fields.Float()
    length = fields.Float()
    area = fields.Float(compute="_compute_area", store=True, readonly=False,
                        help="Defaults to width × height; you may override it.")

    selected_option_ids = fields.Many2many(
        "cpq.option", string="Selected Options",
        domain="[('template_id','=',template_id),('active','=',True)]")
    configuration_line_ids = fields.One2many(
        "cpq.configuration.line", "configuration_id", string="Configuration Lines",
        readonly=True)
    log_ids = fields.One2many(
        "cpq.calculation.log", "configuration_id", string="Calculation Logs",
        readonly=True)

    base_price = fields.Monetary(currency_field="currency_id")
    options_price = fields.Monetary(currency_field="currency_id", readonly=True)
    rules_price = fields.Monetary(
        currency_field="currency_id", readonly=True,
        string="Rules Adjustment")
    discount_amount = fields.Monetary(currency_field="currency_id")
    total_price = fields.Monetary(currency_field="currency_id", readonly=True,
                                  tracking=True)
    cost_total = fields.Monetary(currency_field="currency_id", readonly=True)
    margin_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    margin_percent = fields.Float(string="Margin (%)", readonly=True)

    state = fields.Selection(
        [("draft", "Draft"), ("validated", "Validated"),
         ("quoted", "Quoted"), ("cancelled", "Cancelled")],
        default="draft", required=True, tracking=True)
    validation_message = fields.Text(readonly=True)
    notes = fields.Text()

    @api.depends("width", "height")
    def _compute_area(self):
        for cfg in self:
            cfg.area = (cfg.width or 0.0) * (cfg.height or 0.0)

    @api.onchange("template_id")
    def _onchange_template_id(self):
        if self.template_id:
            self.base_price = self.template_id.base_price
            self.currency_id = self.template_id.currency_id
            self.selected_option_ids = [(5, 0, 0)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "cpq.configuration") or "New"
            if not vals.get("base_price") and vals.get("template_id"):
                tmpl = self.env["cpq.template"].browse(vals["template_id"])
                vals["base_price"] = tmpl.base_price
        configs = super().create(vals_list)
        configs._recalculate()
        return configs

    def write(self, vals):
        res = super().write(vals)
        triggers = {"selected_option_ids", "quantity", "discount_amount",
                    "base_price", "width", "height", "length", "area",
                    "template_id"}
        if not self.env.context.get("cpq_skip_recalc") and triggers & set(vals):
            self.with_context(cpq_skip_recalc=True)._recalculate()
        return res

    # ------------------------------------------------------------ formulas
    def _formula_vars(self, current_total=0.0):
        self.ensure_one()
        return {
            "base_price": self.base_price or 0.0,
            "quantity": self.quantity or 0.0,
            "width": self.width or 0.0,
            "height": self.height or 0.0,
            "length": self.length or 0.0,
            "area": self.area or 0.0,
            "selected_options_count": len(self.selected_option_ids),
            "selected_codes": set(
                self.selected_option_ids.filtered("code").mapped("code")),
            "current_total": current_total,
        }

    def _safe_eval(self, expr, current_total=0.0):
        """Evaluate an admin-authored expression with a controlled variable map.
        Uses Odoo's safe_eval (no builtins, no attribute access) — never raw
        eval. Returns 0.0 / False on error so a bad formula can't crash a quote."""
        if not expr:
            return 0.0
        try:
            return safe_eval(expr, self._formula_vars(current_total))
        except Exception:  # noqa: BLE001
            return 0.0

    def _option_unit_price(self, option):
        self.ensure_one()
        if option.price_type == "fixed":
            return option.fixed_price
        if option.price_type == "percentage":
            return (self.base_price or 0.0) * (option.percentage_value or 0.0) / 100.0
        if option.price_type == "formula":
            return float(self._safe_eval(option.formula_expression) or 0.0)
        return 0.0

    # ----------------------------------------------------------- calculation
    def _recalculate(self):
        Line = self.env["cpq.configuration.line"]
        Log = self.env["cpq.calculation.log"]
        for cfg in self:
            cfg.configuration_line_ids.unlink()
            cfg.log_ids.unlink()
            # 1) build a line per selected option
            options_price = 0.0
            cost_total = 0.0
            line_vals = []
            for opt in cfg.selected_option_ids:
                unit = cfg._option_unit_price(opt)
                options_price += unit
                cost_total += opt.cost or 0.0
                line_vals.append({
                    "configuration_id": cfg.id,
                    "group_id": opt.group_id.id,
                    "option_id": opt.id,
                    "quantity": 1.0,
                    "unit_price": unit,
                    "subtotal": unit,
                })
            Line.create(line_vals)

            qty = cfg.quantity or 0.0
            total = (cfg.base_price + options_price) * qty
            base_cost = (cfg.template_id.base_product_id.standard_price
                         if cfg.template_id.base_product_id else 0.0)
            cost_total = (cost_total + base_cost) * qty

            # 2) apply pricing rules in sequence, logging each effect
            logs = []
            for rule in cfg.template_id.pricing_rule_ids.filtered(
                    "active").sorted("sequence"):
                if not cfg._rule_matches(rule, total):
                    continue
                before = total
                total = cfg._apply_rule(rule, total)
                logs.append({
                    "configuration_id": cfg.id,
                    "rule_id": rule.id,
                    "description": rule.name,
                    "amount_before": before,
                    "amount_after": total,
                    "price_delta": total - before,
                    "message": dict(rule._fields["price_action"].selection).get(
                        rule.price_action),
                })

            # 3) discount + clamp + margins
            total -= cfg.discount_amount or 0.0
            allow_negative = self.env["ir.config_parameter"].sudo().get_param(
                "cpq.allow_negative_price") == "1"
            if total < 0 and not allow_negative:
                logs.append({
                    "configuration_id": cfg.id, "description": "Negative clamp",
                    "amount_before": total, "amount_after": 0.0,
                    "price_delta": -total,
                    "message": "Final price clamped to 0 (negatives disabled).",
                })
                total = 0.0
            Log.create(logs)

            margin = total - cost_total
            cfg.with_context(cpq_skip_recalc=True).write({
                "options_price": options_price * qty,
                "rules_price": total + (cfg.discount_amount or 0.0)
                - (cfg.base_price + options_price) * qty,
                "total_price": total,
                "cost_total": cost_total,
                "margin_amount": margin,
                "margin_percent": (margin / total * 100.0) if total else 0.0,
            })

    def _rule_matches(self, rule, current_total):
        self.ensure_one()
        if rule.condition_type == "always":
            return True
        if not rule.condition_expression:
            return False
        return bool(self._safe_eval(rule.condition_expression, current_total))

    def _apply_rule(self, rule, total):
        self.ensure_one()
        action = rule.price_action
        if action == "add_fixed":
            return total + rule.amount
        if action == "discount_fixed":
            return total - rule.amount
        if action == "add_percentage":
            return total + total * rule.percentage / 100.0
        if action == "discount_percentage":
            return total - total * rule.percentage / 100.0
        if action == "set_price":
            return rule.amount
        if action == "formula":
            return float(self._safe_eval(rule.formula_expression, total) or total)
        return total

    # ----------------------------------------------------------- validation
    def _validation_issues(self):
        """Return (blocking_errors, warnings) for the current selection."""
        self.ensure_one()
        errors, warnings = [], []
        selected = self.selected_option_ids

        if self.template_id.state != "active":
            errors.append("The template is not active.")
        if selected.filtered(lambda o: not o.active):
            errors.append("Inactive options cannot be selected.")

        for group in self.template_id.option_group_ids.filtered("active"):
            chosen = selected.filtered(lambda o: o.group_id == group)
            n = len(chosen)
            if group.is_required and n == 0:
                errors.append("Group '%s' requires a selection." % group.name)
            if group.selection_type == "single" and n > 1:
                errors.append("Group '%s' allows only one option." % group.name)
            if group.selection_type == "multiple":
                if group.min_selection and n < group.min_selection:
                    errors.append("Group '%s' needs at least %s options."
                                  % (group.name, group.min_selection))
                if group.max_selection and n > group.max_selection:
                    errors.append("Group '%s' allows at most %s options."
                                  % (group.name, group.max_selection))

        for rule in self.template_id.compatibility_rule_ids.filtered("active"):
            if rule._violated(selected):
                msg = rule._default_message()
                if rule.severity == "blocking":
                    errors.append(msg)
                else:
                    warnings.append(msg)
        return errors, warnings

    # ------------------------------------------------------------- UI actions
    def action_recalculate(self):
        self._recalculate()
        return True

    def action_validate(self):
        for cfg in self:
            if cfg.state == "cancelled":
                raise UserError("A cancelled configuration cannot be validated.")
            cfg._recalculate()
            errors, warnings = cfg._validation_issues()
            if errors:
                raise UserError("Configuration is not valid:\n• "
                                + "\n• ".join(errors))
            cfg.write({
                "state": "validated",
                "validation_message": ("Warnings:\n• " + "\n• ".join(warnings))
                if warnings else "Valid configuration.",
            })

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_to_draft(self):
        self.write({"state": "draft", "validation_message": False})

    def _quote_description(self):
        """Human-readable summary of the selected options — reused by the
        optional smart_cpq_sale integration."""
        self.ensure_one()
        lines = ["%s — %s" % (self.template_id.name, self.name)]
        for line in self.configuration_line_ids:
            lines.append("  • %s: %s" % (line.group_id.name, line.option_id.name))
        return "\n".join(lines)
