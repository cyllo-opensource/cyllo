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
    'name': 'Cyllo Map',
    'summary': "Integrate map view functionalities.",
    'description': "The module aims to enhance functionality by integrating map viewing capabilities. Users can"
                   "visualize geographical data and utilize location-based coordinates for various purposes.",
    'version': "1.0",
    'author': "Cyllo",
    'company': "Cyllo",
    'maintainer': "Cyllo",
    'website': "https://www.cyllo.com",
    'depends': ['hr', 'website', 'contacts', 'base_geolocalize'],
    'icon': '/cyllo_map/static/description/maps.svg',
    'data': [
        'views/res_partner_views.xml',
        'views/openstreet_map_snippet.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cyllo_map/static/src/js/address_from_map.js',
            'cyllo_map/static/src/xml/address_from_map.xml',
            'cyllo_map/static/src/js/address_autofill.js',
            'cyllo_map/static/src/xml/address_autofill.xml',
            'cyllo_map/static/src/scss/style.scss',
            'cyllo_map/static/src/js/lib/leaflet/leaflet.js',
            'cyllo_map/static/src/js/lib/leaflet/leaflet.css',
            'cyllo_map/static/src/js/map_view_controller.js',
            'cyllo_map/static/src/js/map_view_renderer.js',
            'cyllo_map/static/src/js/map_view_arch_parser.js',
            'cyllo_map/static/src/js/map_view.js',
            'cyllo_map/static/src/xml/map_view_controller.xml',
            'cyllo_map/static/src/xml/map_view_renderer.xml',
            'cyllo_map/static/src/xml/map_view_arch_parser.xml',
        ],
        'web.assets_frontend': [
            'cyllo_map/static/src/js/lib/leaflet/leaflet.js',
            'cyllo_map/static/src/js/lib/leaflet/leaflet.css',
            'cyllo_map/static/src/js/openstreet_map_snippet.js',
        ],
    },
    "uninstall_hook": "uninstall_hook",
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
