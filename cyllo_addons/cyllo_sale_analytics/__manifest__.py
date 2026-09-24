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
    'name': 'Cyllo Sale Analytics',
    'category': 'Extra Tools',
    'summary': """
        This module helps businesses to identify customers who are at risk of discontinuing their relationship with the company.
    """,
    'description': """
        By analyzing historical data and relevant factors of the customers, churn prediction dashboard 
        helps organizations proactively take measures to retain valuable customers and reduce attrition, ultimately improving 
        customer retention and business profitability.
    """,
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['cyllo_analytics', 'sale_management', 'stock', 'cyllo_ai'],
    "external_dependencies": {
        'python': ['pandas', 'scikit-learn', 'prophet', 'statsmodels', 'shap', 'xgboost', 'lightgbm']
    },
    'icon': '/cyllo_sale_analytics/static/description/sales-analytics.svg',
    'data': [
        'security/ir.model.access.csv',
        'data/algo_config_data.xml',
        'reports/churn_prediction_templates.xml',
        'reports/demand_prediction_template.xml',
        'reports/sale_prediction_templates.xml',
        'views/cyllo_sale_analytics_menus.xml',
        'views/algo_config_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap',
            'cyllo_sale_analytics/static/src/css/style.css',
            'cyllo_sale_analytics/static/src/css/sales_forecast_news.css',
            # loaded after style.css so the churn overrides win on equal specificity
            'cyllo_sale_analytics/static/src/css/churn_dashboard.css',
            'cyllo_sale_analytics/static/src/js/churn_prediction.js',
            'cyllo_sale_analytics/static/src/js/sales_prediction.js',

            'cyllo_sale_analytics/static/src/js/demand_prediction.js',
            'cyllo_sale_analytics/static/src/js/customer_details.js',
            'cyllo_sale_analytics/static/src/xml/churn_prediction.xml',
            'cyllo_sale_analytics/static/src/xml/customer_details.xml',
            'cyllo_sale_analytics/static/src/xml/demand_prediction.xml',
            'cyllo_sale_analytics/static/src/xml/sales_prediction.xml',

        ],
    },
    'images': [],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': True,
}
