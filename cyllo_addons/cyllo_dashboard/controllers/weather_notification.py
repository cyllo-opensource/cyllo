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
import geocoder
import requests
from requests.exceptions import ConnectionError, Timeout

from odoo.http import Controller, request, route


class WeatherNotification(Controller):
    """Class defined to fetch weather details based on location"""

    @route('/weather/notification/check', type='json', auth="public",
                methods=['POST'])
    def weather_notification(self):
        """Controller for fetching weather data"""
        try:
            if request.env.user.location_set == 'auto' and request.env.user.api_key:
                location = geocoder.ip('me')
                if location and location.latlng:
                    lat = round(location.latlng[0], 2)
                    lng = round(location.latlng[1], 2)
                    url = (
                        f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid='
                        f'{request.env.user.api_key}')
                    try:
                        # Set timeout to 5 seconds
                        response = requests.get(url, timeout=5)
                        if response.status_code == 200:
                            return response.json()
                        else:
                            return {'data': False}
                    except Timeout:
                        return {'data': False, 'message': 'Request timed out.'}
                else:
                    return {'data': False,
                            'message': 'Failed to get location data.'}
            elif request.env.user.location_set == 'manual' and request.env.user.api_key:
                url = (
                    f'https://api.openweathermap.org/data/2.5/weather?q={request.env.user.city}&appid='
                    f'{request.env.user.api_key}')
                try:
                    # Set timeout to 5 seconds
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        return response.json()
                    else:
                        return response.json()
                except Timeout:
                    return {'data': False, 'message': 'Request timed out.'}
        except ConnectionError:
            return {'data': False,
                    'message': 'No internet connection. Please check your internet connectivity.'}
        else:
            return {'data': False}
