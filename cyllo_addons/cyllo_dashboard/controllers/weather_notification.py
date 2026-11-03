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
import datetime

import geocoder
import pytz
import requests
from requests.exceptions import ConnectionError, Timeout

from odoo.http import Controller, request, route


class WeatherNotification(Controller):
    """Class defined to fetch weather details based on location"""

    def _augment_current(self, payload, forecast_url):
        """Attach the derived widgets' data (forecast steps) to the
        current-weather payload — best-effort; the current-weather card
        must never break because of it."""
        payload['forecast'] = self._owm_forecast(forecast_url)
        return payload

    def _owm_forecast(self, forecast_url):
        """Best-effort fetch of the next 3-hour forecast steps.

        Any failure here must never break the current-weather response,
        so every problem degrades to an empty list.
        """
        try:
            response = requests.get(forecast_url, timeout=5)
            if response.status_code != 200:
                return []
            payload = response.json()
            # dt is seconds since epoch (UTC); render it in the user's
            # timezone so the KPI chips show the user's clock (17:30),
            # not decoder-server time.
            user_tz = pytz.timezone(request.env.user.tz or 'UTC')
            steps = []
            for entry in payload.get('list', [])[:6]:
                local_dt = datetime.datetime.fromtimestamp(entry['dt'], user_tz)
                # Label follows the reference strip style: "9 am" / "12 pm".
                label = local_dt.strftime('%-I') + (
                    ' am' if local_dt.hour < 12 else ' pm')
                weather = entry.get('weather') or [{}]
                icon_code = weather[0].get('icon') or '02d'
                steps.append({
                    'time': label,
                    'temp': round(entry['main']['temp']),
                    'condition': weather[0].get('main') or '',
                    # Probability of precipitation (0-1 in the payload).
                    'pop': int(round((entry.get('pop') or 0) * 100)),
                    'icon': 'https://openweathermap.org/img/wn/'
                            + icon_code + '@2x.png',
                })
            return steps
        except Exception:
            return []

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
                    forecast_url = (
                        f'https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lng}'
                        f'&appid={request.env.user.api_key}&units=metric')
                    try:
                        # Set timeout to 5 seconds
                        response = requests.get(url, timeout=5)
                        if response.status_code == 200:
                            return self._augment_current(
                                response.json(), forecast_url)
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
                forecast_url = (
                    f'https://api.openweathermap.org/data/2.5/forecast?q={request.env.user.city}'
                    f'&appid={request.env.user.api_key}&units=metric')
                try:
                    # Set timeout to 5 seconds
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        return self._augment_current(
                            response.json(), forecast_url)
                    else:
                        return response.json()
                except Timeout:
                    return {'data': False, 'message': 'Request timed out.'}
        except ConnectionError:
            return {'data': False,
                    'message': 'No internet connection. Please check your internet connectivity.'}
        else:
            return {'data': False}
