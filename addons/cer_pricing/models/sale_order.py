# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

ICP_VALIDITY_DAYS_KEY = "cer_base.quote_validity_days"


class SaleOrder(models.Model):
    _inherit = "sale.order"

    cer_date_from = fields.Date(string="Fecha Entrada")
    cer_date_to = fields.Date(string="Fecha Salida")
    cer_participants = fields.Integer(string="Participantes", default=0)

    cer_discount_id = fields.Many2one("cer.pricing.discount", string="Descuento CER")

    cer_stay_nights = fields.Integer(string="Noches", compute="_compute_cer_stay", store=True, readonly=True)
    cer_stay_days = fields.Integer(string="Días", compute="_compute_cer_stay", store=True, readonly=True)
    cer_stay_display = fields.Char(string="Estadía", compute="_compute_cer_stay_display", store=True, readonly=True)

    def _cer_get_quote_validity_days(self):
        self.ensure_one()
        icp = self.env["ir.config_parameter"].sudo()
        scoped = icp.get_param(f"{ICP_VALIDITY_DAYS_KEY}__company_{self.company_id.id}", default=None)
        if scoped not in (None, ""):
            return int(scoped or 0)
        return int(icp.get_param(ICP_VALIDITY_DAYS_KEY, 7) or 7)

    @api.model
    def _cer_add_business_days(self, start_date, business_days):
        """Suma días hábiles (lun-vie), excluyendo sábados y domingos."""
        current = start_date
        remaining = int(max(0, business_days or 0))
        while remaining > 0:
            current += timedelta(days=1)
            if current.weekday() < 5:
                remaining -= 1
        return current

    def _cer_compute_validity_business_date(self):
        self.ensure_one()
        base_date = fields.Date.context_today(self)
        days = self._cer_get_quote_validity_days()
        return self._cer_add_business_days(base_date, days)

    @api.depends("cer_date_from", "cer_date_to")
    def _compute_cer_stay(self):
        """
        Regla definitiva:
          - Noches = (Salida - Entrada) (no inclusivo)
          - Días   = Noches + 1 (inclusivo)

        Ejemplo:
          Entrada 10 / Salida 11 => Noches=1, Días=2
        """
        for order in self:
            if order.cer_date_from and order.cer_date_to and order.cer_date_to >= order.cer_date_from:
                nights = (order.cer_date_to - order.cer_date_from).days
                days = nights + 1
                order.cer_stay_nights = int(nights)
                order.cer_stay_days = int(days)
            else:
                order.cer_stay_nights = 0
                order.cer_stay_days = 0

    @api.depends("cer_stay_days")
    def _compute_cer_stay_display(self):
        for order in self:
            order.cer_stay_display = (_("%s día(s)") % order.cer_stay_days) if order.cer_stay_days else ""

    @api.constrains("cer_date_from", "cer_date_to")
    def _check_cer_dates(self):
        for order in self:
            if order.cer_date_from and order.cer_date_to and order.cer_date_to < order.cer_date_from:
                raise ValidationError(_("La Fecha Salida no puede ser menor que la Fecha Entrada."))

    @api.onchange("partner_id")
    def _onchange_partner_id_cer_discount(self):
        for order in self:
            if order.partner_id and not order.cer_discount_id:
                # Proponer descuento por defecto del cliente
                order.cer_discount_id = order.partner_id.cer_discount_id
            if not order.validity_date:
                order.validity_date = order._cer_compute_validity_business_date()

    @api.onchange("cer_date_from", "cer_date_to", "cer_participants", "cer_discount_id")
    def _onchange_cer_header_recompute(self):
        for order in self:
            order._cer_sync_lines()

    def _cer_find_season(self):
        self.ensure_one()
        Season = self.env["cer.pricing.season"]
        if not self.cer_date_from:
            return Season.browse()
        return Season.search(
            [
                ("active", "=", True),
                ("company_id", "=", self.company_id.id),
                ("date_from", "<=", self.cer_date_from),
                ("date_to", ">=", self.cer_date_from),
            ],
            order="priority desc, id desc",
            limit=1,
        )

    def _cer_sync_lines(self):
        """Recalcula (en memoria) cantidades CER y aplica tarifa/temporada + descuento a las líneas."""
        Engine = self.env["cer.pricing.engine"]
        Rate = self.env["cer.pricing.rate"]

        for order in self:
            # no hacer nada sin líneas
            lines = order.order_line.filtered(lambda l: not l.display_type and l.product_id)
            if not lines:
                continue

            season = order._cer_find_season()
            rate_map = {}
            if season:
                tmpl_ids = list(set(lines.mapped("product_id.product_tmpl_id").ids))
                rates = Rate.search(
                    [
                        ("active", "=", True),
                        ("company_id", "=", order.company_id.id),
                        ("season_id", "=", season.id),
                        ("product_tmpl_id", "in", tmpl_ids),
                    ]
                )
                rate_map = {r.product_tmpl_id.id: r.price for r in rates}

            discount_pct = float(order.cer_discount_id.discount_percent) if order.cer_discount_id else 0.0

            for line in lines:
                # Aplica precio temporada si existe
                if season:
                    rp = rate_map.get(line.product_id.product_tmpl_id.id)
                    if rp is not None:
                        line.price_unit = rp
                    line.cer_season_id = season.id

                # Aplica descuento fijo a la línea (porcentaje).
                # Si no hay descuento CER en cabecera, forzamos 0 para evitar arrastres.
                if not order.cer_discount_id:
                    line.discount = 0.0
                elif line.cer_apply_discount:
                    line.discount = discount_pct

                # Recalcula cantidad interna según modo (sin necesidad de wizard)
                if order.cer_date_from and order.cer_date_to:
                    participants = int(line.cer_participants or order.cer_participants or 0)
                    effective_charge_mode = line.cer_charge_mode or "fixed"

                    payload = Engine.compute_line_payload(
                        charge_mode=effective_charge_mode,
                        participants=participants,
                        min_people=line.cer_min_people or 0,
                        date_from=order.cer_date_from,
                        date_to=order.cer_date_to,
                    )
                    computed_qty = payload.get("qty", line.product_uom_qty)

                    # Siempre actualizar informativos (Noche/Día) aunque la qty sea manual
                    line.cer_qty_computed = payload.get("qty", 0.0)
                    line.cer_nights = payload.get("nights", 0)
                    line.cer_days = payload.get("days", 0)
                    line.cer_participants = payload.get("participants", participants)

                    # En person_day/day forzamos cantidad calculada para mantener coherencia comercial.
                    # En otros modos, respetamos el flag de qty automática.
                    if effective_charge_mode in ("person_day", "day"):
                        line.product_uom_qty = computed_qty
                    elif line.cer_auto_qty:
                        line.product_uom_qty = computed_qty

                    # Recalcular importes para evitar subtotales desfasados en UI/PDF.
                    line._compute_amount()
                else:
                    # Sin fechas: limpiar informativos para evitar datos antiguos
                    line.cer_qty_computed = 0.0
                    line.cer_nights = 0
                    line.cer_days = 0

    @api.model_create_multi
    def create(self, vals_list):
        normalized = []
        for vals in vals_list:
            data = dict(vals)
            if not data.get("validity_date"):
                pseudo = self.new(data)
                data["validity_date"] = pseudo._cer_compute_validity_business_date()
            normalized.append(data)
        return super().create(normalized)

    def write(self, vals):
        res = super().write(vals)
        # Recalcular al guardar si cambian campos CER clave (sin wizard)
        if set(vals).intersection({"cer_date_from", "cer_date_to", "cer_participants", "cer_discount_id", "partner_id"}):
            for order in self:
                # Evitar recursión si write viene desde sync
                if self.env.context.get("cer_skip_sync"):
                    continue
                order.with_context(cer_skip_sync=True)._cer_sync_lines()
        return res
