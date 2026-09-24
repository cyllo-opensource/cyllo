# -*- coding: utf-8 -*-
from odoo import fields, models


class HelpdeskTeam(models.Model):
    """Project settings made available only with the project integration."""

    _inherit = 'helpdesk.team'

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        help="Default project for tasks created from this team's tickets.",
    )
