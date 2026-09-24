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
import clicksend_client
import random
from ast import literal_eval
from clicksend_client import SmsMessage
from twilio.rest import Client

from odoo import _, http
from odoo.http import request
from odoo.addons.web.controllers.home import ensure_db, Home

SIGN_UP_REQUEST_PARAMS = {'db', 'login', 'debug', 'token', 'message', 'error',
                          'scope', 'mode',
                          'redirect', 'redirect_hostname', 'email', 'name',
                          'partner_id',
                          'password', 'confirm_password', 'city', 'country_id',
                          'lang', 'signup_email', 'otp_success'}


class LoginController(Home):
    """
    Controller that handles OTP login functionality.
    """

    @http.route()
    def web_login(self, *args, **kw):
        """
        Overrides the web_login method to add OTP login functionality.
        :return: Response object with OTP login functionality added.
        """
        ensure_db()
        response = super().web_login(*args, **kw)
        if response.is_qweb:
            if hasattr(request, 'website'):
                response.qcontext[
                    'is_active_sms'] = request.website.is_active_sms
            else:
                response.qcontext['is_active_sms'] = True
        return response

    @http.route(['/web/otp/login'], type='http', auth='public', website=True,
                csrf=False, csrf_token=None)
    def login_redirect(self):
        """
           Redirects to the OTP login page.

           :return: Rendered page for OTP login.
        """
        return request.render('cyllo_sms_gateway.login_otp')

    @http.route('/web/login/otp', type='http', auth="public", website=True,
                csrf=False, csrf_token=None)
    def otp_login(self):
        """
        Handles the OTP login process.
        :return: Rendered page for OTP verification.
        """
        values = {k: v for k, v in request.params.items() if
                  k in SIGN_UP_REQUEST_PARAMS}
        request.session['login_email'] = request.params['login']
        user = request.env['res.users'].sudo().search(
            [('login', '=', request.session['login_email'])])
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        request.session['otp'] = otp
        if user and request.website.is_active_sms:
            gateway = request.website.gateway_id
            phone_number = user.partner_id.mobile or user.partner_id.phone
            if phone_number:
                success = "OTP Sent Successfully"
                error = "Some error occurred try again later or contact admin"
                if gateway.sudo().name == 'TWILIO':
                    try:
                        client = Client(
                            gateway.with_user(user).twilio_account_sid,
                            gateway.with_user(user).twilio_auth_token)
                        client.messages.create(body=f"Your login OTP is {otp}",
                                               from_=gateway.with_user(
                                                   user).twilio_phone_number,
                                               to=phone_number)
                        values['otp_success'] = success
                        return request.render('cyllo_sms_gateway.verify_otp',
                                              values)
                    except Exception as e:
                        values['error'] = error
                        return request.render('cyllo_sms_gateway.login_otp',
                                              values)
                # TODO
                # elif gateway.name == 'D7':
                #     payload = json.dumps({
                #         "messages": [
                #             {"channel": "sms", "recipients": [phone_number],
                #              "content": f"Your login OTP is {otp}",
                #              "msg_type": "text",
                #              "data_coding": "text"}],
                #         "message_globals": {
                #             "originator": "SignOTP",
                #             "report_url": "https://the_url_to_recieve_delivery_report.com"
                #         }
                #     })
                #     headers = {'Content-Type': 'application/json',
                #                'Accept': 'application/json',
                #                'Authorization': 'Bearer ' + gateway.with_user(
                #                    user).d7_api}
                #     try:
                #         response = requests.request("POST",
                #                                     "https://api.d7networks.com/messages/v1/send",
                #                                     headers=headers,
                #                                     data=payload)
                #         if response.status_code == 200:
                #             values['otp_success'] = success
                #             return request.render(
                #                 'cyllo_sms_gateway.verify_otp')
                #         else:
                #             values['error'] = error
                #             return request.render('cyllo_sms_gateway.login_otp',
                #                                   values)
                #     except:
                #         values[
                #             'error'] = "Some error occurred contact try a gain later or contact admin"
                #         return request.render('cyllo_sms_gateway.login_otp',
                #                               values)
                elif gateway.name == 'CLICK SEND':
                    configuration = clicksend_client.Configuration()
                    configuration.username = gateway.with_company(
                        user.company_id).click_send_email
                    configuration.password = gateway.with_company(
                        user.company_id).click_send_api
                    api_instance = clicksend_client.SMSApi(
                        clicksend_client.ApiClient(configuration))
                    sms_message = SmsMessage(source="php",
                                             body=f"Your login OTP is {otp}",
                                             to=phone_number,
                                             schedule=1436874701)
                    sms_messages = clicksend_client.SmsMessageCollection(
                        messages=[sms_message])
                    try:
                        response = api_instance.sms_send_post(sms_messages)
                        response = response.replace("\'", "\"")
                        literal_eval(response)
                        response = literal_eval(response)
                        status = response['data']['messages'][0]['status']
                        if status == "INSUFFICIENT_CREDIT":
                            values['error'] = error
                            return request.render('cyllo_sms_gateway.login_otp',
                                                  values)
                        values['otp_success'] = success
                        return request.render('cyllo_sms_gateway.verify_otp')
                    except:
                        values['error'] = error
                        return request.render('cyllo_sms_gateway.login_otp',
                                              values)
            else:
                values[
                    'error'] = "Phone number does not exist in registry contact admin"
                return request.render('cyllo_sms_gateway.login_otp', values)
        else:
            values['error'] = "Email address does not exist"
            return request.render('cyllo_sms_gateway.login_otp', values)

    @http.route('/web/login/verify_otp', type='http', auth="public",
                website=True, csrf=False, csrf_token=None)
    def verify_otp(self):
        """
        Verifies the OTP and authenticates the user if OTP is correct.
        :return: Redirect response after successful OTP verification or error
        page. """
        otp = request.params['otp']
        if otp == request.session.get('otp'):
            session = request.session
            session.authenticate_without_passwd(request.env.cr.dbname,
                                                request.session.get(
                                                    'login_email'))
            return request.redirect('/')
        else:
            values = {k: v for k, v in request.params.items() if
                      k in SIGN_UP_REQUEST_PARAMS}
            values['error'] = _("Wrong OTP")
            return request.render('cyllo_sms_gateway.verify_otp', values)

    @http.route('/twilio/status', type='http', auth='public', methods=['POST'],
                csrf=False)
    def twilio_status_update(self, **post):
        message_sid = post.get('MessageSid')
        status = post.get('MessageStatus')
        # Find and update the SMS record in your model
        sms_record = request.env['sms.history'].sudo().search(
            [('sid', '=', message_sid)], limit=1)
        if sms_record:
            sms_record.write({'sms_status': status})

    @http.route('/clicksend/status', type='http', auth='public',
                methods=['POST'],
                csrf=False)
    def clicksend_status_update(self, **post):
        message_sid = post.get('message_id')
        status = post.get('status')
        sms_record = request.env['sms.history'].sudo().search(
            [('sid', '=', message_sid)], limit=1)
        if sms_record:
            sms_record.write({'sms_status': status})

    @http.route('/D7/status', type='http', auth='public',
                methods=['POST'],
                csrf=False)
    def d7_status_update(self, **post):
        request_id = post.get('request_id')
        status = post.get('status')
        sms_record = request.env['sms.history'].sudo().search(
            [('sid', '=', request_id)], limit=1)
        if sms_record:
            sms_record.write({'sms_status': status})
