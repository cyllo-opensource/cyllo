# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
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
{
    "name": "Cyllo AI Analytics",
    "summary": "Analytics tools for the Cyllo AI assistant (chart recommendation).",
    "description": "Contributes analytics capabilities to the Cyllo AI "
                   "assistant via its tool-extension seam — starting with "
                   "chart recommendation. Adds no changes to cyllo_ai itself.",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    "category": "Extra Tools",
    "depends": ["cyllo_ai", "cyllo_analytics"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "cyllo_ai_analytics/static/src/js/ai_chart_suggestions.js",
            "cyllo_ai_analytics/static/src/js/ai_chart_tile.js",
            "cyllo_ai_analytics/static/src/js/ai_quick_dashboard.js",
            "cyllo_ai_analytics/static/src/js/dashboard_insight.js",
            "cyllo_ai_analytics/static/src/xml/ai_quick_dashboard.xml",
            "cyllo_ai_analytics/static/src/css/ai_chart_suggestions.css",
            "cyllo_ai_analytics/static/src/css/ai_quick_dashboard.css",
        ],
    },
    'license': 'LGPL-3',
    "installable": True,
    "application": False,
    "auto_install": False,
}
