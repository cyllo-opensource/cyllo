# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
#    Author: Cyllo(<https://www.cyllo.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import http, fields, _
from odoo.http import request


class FrontdeskMeetingController(http.Controller):

    def _render_response_page(self, title, heading, badge_text, icon_class, icon_svg, visitor, info_message):
        company_row = f"""
        <div class="detail-row">
            <span class="detail-label">Company</span>
            <span class="detail-value">{visitor.company}</span>
        </div>
        """ if visitor.company else ""
        
        planned_time = visitor._format_datetime(visitor.expected_arrival) if visitor.expected_arrival else _("N/A")
        host_name = visitor.host_id.name if visitor.host_id else _("N/A")
        purpose = visitor.purpose or _("N/A")

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --cyllo-green: #6abf4b;
            --cyllo-green-dark: #57a33a;
            --cyllo-green-light: #edf7e8;
            --bg: #f4f5f7;
            --card-bg: #ffffff;
            --card-border: #e2e6ea;
            --text-primary: #2c3345;
            --text-secondary: #6c7a8d;
            --success: #6abf4b;
            --danger: #e05252;
            --warning: #e8a020;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Inter', sans-serif;
            background: var(--bg);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: var(--text-primary);
            padding: 24px;
        }}

        .container {{
            max-width: 480px;
            width: 100%;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 36px 32px;
            text-align: center;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.07);
            animation: fadeIn 0.4s ease forwards;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(12px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
        }}

        .icon-wrapper {{
            width: 72px;
            height: 72px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
        }}

        .icon-wrapper.success {{
            background: #edf7e8;
            border: 2px solid var(--success);
            color: var(--success);
        }}

        .icon-wrapper.danger {{
            background: #fdf0f0;
            border: 2px solid var(--danger);
            color: var(--danger);
        }}

        .icon-wrapper.warning {{
            background: #fef8ec;
            border: 2px solid var(--warning);
            color: var(--warning);
        }}

        .icon-wrapper svg {{
            width: 34px;
            height: 34px;
        }}

        h1 {{
            font-size: 22px;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 10px;
        }}

        .status-badge {{
            display: inline-block;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 24px;
            text-transform: uppercase;
            letter-spacing: 0.6px;
        }}

        .status-badge.success {{ background: #edf7e8; color: #4a9933; }}
        .status-badge.danger  {{ background: #fdf0f0; color: #c03030; }}
        .status-badge.warning {{ background: #fef8ec; color: #b07010; }}

        .details-card {{
            background: #f9fafb;
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 4px 16px;
            margin-bottom: 24px;
            text-align: left;
        }}

        .detail-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 11px 0;
            border-bottom: 1px solid #eaecef;
            font-size: 13.5px;
        }}

        .detail-row:last-child {{
            border-bottom: none;
        }}

        .detail-label {{
            color: var(--text-secondary);
            font-weight: 400;
        }}

        .detail-value {{
            color: var(--text-primary);
            font-weight: 600;
            text-align: right;
            max-width: 60%;
        }}

        .info-message {{
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon-wrapper {icon_class}">
            {icon_svg}
        </div>
        <h1>{heading}</h1>
        <div class="status-badge {icon_class}">{badge_text}</div>

        <div class="details-card">
            <div class="detail-row">
                <span class="detail-label">Visitor</span>
                <span class="detail-value">{visitor.visitor_name}</span>
            </div>
            {company_row}
            <div class="detail-row">
                <span class="detail-label">Purpose</span>
                <span class="detail-value">{purpose}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Planned Arrival</span>
                <span class="detail-value">{planned_time}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Host</span>
                <span class="detail-value">{host_name}</span>
            </div>
        </div>

        <p class="info-message">{info_message}</p>
    </div>
</body>
</html>
"""
        return request.make_response(html_content, headers=[('Content-Type', 'text/html')])

    @http.route('/frontdesk/meeting/approve/<string:token>', type='http', auth='public')
    def approve_meeting(self, token, **kwargs):
        visitor = request.env['frontdesk.visitor'].sudo().search([('access_token', '=', token)], limit=1)
        if not visitor:
            return request.not_found()

        if visitor.state != 'draft':
            return self._render_already_processed(visitor)

        approved_time = fields.Datetime.now()
        visitor.sudo().write({
            'state': 'planned',
            'approved_by_id': visitor.host_id.id if visitor.host_id else False,
            'approved_datetime': approved_time
        })
        
        formatted_date = visitor._format_datetime(approved_time)
        host_name = visitor.host_id.name if visitor.host_id else _("Unknown Host")
        message = _("Meeting request approved by %s on %s.") % (host_name, formatted_date)
        visitor.sudo().message_post(body=message)

        # Send notification to the host user
        if visitor.host_id and visitor.host_id.user_id:
            visitor.sudo().message_post(
                body=message,
                partner_ids=[visitor.host_id.user_partner_id.id]
            )

        icon_svg = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
        </svg>"""

        return self._render_response_page(
            title=_("Meeting Approved"),
            heading=_("Meeting Approved"),
            badge_text=_("Approved"),
            icon_class="success",
            icon_svg=icon_svg,
            visitor=visitor,
            info_message=_("The visitor meeting request has been successfully approved and scheduled.")
        )

    @http.route('/frontdesk/meeting/reject/<string:token>', type='http', auth='public')
    def reject_meeting(self, token, **kwargs):
        visitor = request.env['frontdesk.visitor'].sudo().search([('access_token', '=', token)], limit=1)
        if not visitor:
            return request.not_found()

        if visitor.state != 'draft':
            return self._render_already_processed(visitor)

        rejected_time = fields.Datetime.now()
        visitor.sudo().write({
            'state': 'cancelled',
            'rejected_by_id': visitor.host_id.id if visitor.host_id else False,
            'rejected_datetime': rejected_time
        })
        
        formatted_date = visitor._format_datetime(rejected_time)
        host_name = visitor.host_id.name if visitor.host_id else _("Unknown Host")
        message = _("Meeting request rejected by %s on %s.") % (host_name, formatted_date)
        visitor.sudo().message_post(body=message)

        # Send notification to the host user
        if visitor.host_id and visitor.host_id.user_id:
            visitor.sudo().message_post(
                body=message,
                partner_ids=[visitor.host_id.user_partner_id.id]
            )

        icon_svg = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>"""

        return self._render_response_page(
            title=_("Meeting Rejected"),
            heading=_("Meeting Rejected"),
            badge_text=_("Rejected"),
            icon_class="danger",
            icon_svg=icon_svg,
            visitor=visitor,
            info_message=_("The visitor meeting request has been rejected and cancelled.")
        )

    def _render_already_processed(self, visitor):
        icon_svg = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>"""

        state_labels = {
            'draft': _('Draft'),
            'planned': _('Approved / Planned'),
            'checked_in': _('Checked In'),
            'checked_out': _('Checked Out'),
            'cancelled': _('Rejected / Cancelled')
        }
        badge_text = state_labels.get(visitor.state, _('Processed'))
        icon_class = "warning"
        if visitor.state == 'cancelled':
            icon_class = "danger"
        elif visitor.state in ('planned', 'checked_in', 'checked_out'):
            icon_class = "success"

        return self._render_response_page(
            title=_("Already Processed"),
            heading=_("Already Processed"),
            badge_text=badge_text,
            icon_class=icon_class,
            icon_svg=icon_svg,
            visitor=visitor,
            info_message=_("This meeting request has already been processed and cannot be modified again.")
        )
