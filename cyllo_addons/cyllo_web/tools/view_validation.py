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
import os

from lxml import etree

from odoo.tools.view_validation import _logger, _relaxng_cache
from odoo.tools import view_validation
from odoo import tools



def relaxng(view_type):
    """ Return a validator for the given view type, or None. """
    if view_type not in _relaxng_cache:
        path = 'base' if view_type not in ("graph","pivot") else "cyllo_web"
        with tools.file_open(os.path.join(path, 'rng', '%s_view.rng' % view_type)) as frng:
            try:
                relaxng_doc = etree.parse(frng)
                if view_type in ("graph", "pivot"):
                    # These custom schemas extend the base schema. Resolve the
                    # include through Odoo's addon paths; a relative
                    # ``common.rng`` points to cyllo_web/rng/common.rng, which
                    # is not part of this addon.
                    common_rng = tools.file_path('base/rng/common.rng')
                    for include in relaxng_doc.xpath(
                        '//rng:include[@href="common.rng"]',
                        namespaces={'rng': 'http://relaxng.org/ns/structure/1.0'},
                    ):
                        include.set('href', common_rng)
                _relaxng_cache[view_type] = etree.RelaxNG(relaxng_doc)
            except Exception:
                _logger.exception('Failed to load RelaxNG XML schema for views validation')
                _relaxng_cache[view_type] = None
    return _relaxng_cache[view_type]


view_validation.relaxng = relaxng
