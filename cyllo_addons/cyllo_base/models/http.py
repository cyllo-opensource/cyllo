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
import collections.abc
from werkzeug.exceptions import (NotFound)

from odoo.http import JsonRPCDispatcher, serialize_exception, SessionExpiredException


class RPCDispatcher(JsonRPCDispatcher):
    """A dispatcher class for handling JSON-RPC requests.
    This class extends JsonRPCDispatcher and provides additional functionality
    for handling errors and dispatching requests of type 'json'."""
    routing_type = 'json'

    def handle_error(self, exc: Exception) -> collections.abc.Callable:
        """
        Handle any exception that occurred while dispatching a request to
        a `type='json'` route. Also handle exceptions that occurred when
        no route matched the request path, that no fallback page could
        be delivered and that the request ``Content-Type`` was json.
        :param exc: the exception that occurred.
        :returns: a WSGI application
        """
        error = {
            # This code is the JSON-RPC level code, it is distinct from the
            # HTTP status code. This code is ignored and the value 200
            # (while misleading) is totally arbitrary.
            'code': 200,
            'message': "Cyllo Server Error",
            'data': serialize_exception(exc),
        }
        if isinstance(exc, NotFound):
            error['code'] = 404
            error['message'] = "404: Not Found"
        elif isinstance(exc, SessionExpiredException):
            error['code'] = 100
            error['message'] = "Cyllo Session Expired"
        return self._response(error=error)
