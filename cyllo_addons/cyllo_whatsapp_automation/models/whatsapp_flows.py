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
import io
import requests
import json
import inflect
import xlsxwriter
from odoo.exceptions import ValidationError
from odoo import _, api, fields, models


class WhatsappFlows(models.Model):
    """
    Model for managing WhatsApp interaction flows within Odoo.

    This model organizes and tracks various WhatsApp communication flows, allows
    to set up structured whatsapp flows, manage flow statuses,
    and create screens for whatsapp flows.
    """
    _name = 'whatsapp.flows'
    _description = "Whatsapp Flows"

    name = fields.Char(
        string='Flow Name',
        required=True,
        help='The name of the WhatsApp flow. This will be used for easy '
             'identification of the flow.'
    )
    flow_name = fields.Char(
        string='Generated Flow Name',
        help='The actual name of whatsapp flow generated based on whatsapp '
             'guidelines',
        compute='_compute_flow_name')
    active = fields.Boolean(
        string='Active',
        default=True,
        help='The field describes the record is active or not'
    )
    flow_id = fields.Char(
        string='Flow Identifier',
        help='A unique identifier for the WhatsApp flow, primarily used for '
             'internal references or API integrations.'
    )
    screen_ids = fields.One2many(
        comodel_name='whatsapp.flows.screens',
        inverse_name='flow_id',
        string='Screens',
        help='Specify the screens for this whatsapp flow'
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed'),
         ('published', 'Published'), ('deprecate', 'Deprecated')],
        default='draft',
        string='Flow Status',
        help='Defines the current status of the WhatsApp flow.'
    )
    user_id = fields.Many2one(
        string='Responsible User',
        comodel_name='res.users',
        default=lambda self: self.env.user,
        help='The user is responsible for this flow'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.company,
        string='Associated Company',
        help='Select the company under which this WhatsApp flow is managed.'
    )
    response_done_count = fields.Integer(
        string="Response",
        compute="_compute_response_done_count",
        help='The count of completed responses in this flow.'
    )

    @api.model
    def get_xlsx_report(self, data, response):
        """
        Generate an XLSX report based on the provided data for a WhatsApp flow.

        This method processes the given data and generates a report in Excel format
        containing details of the flow, screens, and user responses. The generated
        report is streamed as an XLSX file in the HTTP response.

        Args:
            data (dict or str): The data to be used for generating the report. This can be
                                either a dictionary or a JSON string. The data should contain
                                information about the flow, its screens, and the user responses.
            response (object): The response object to stream the generated XLSX file. This is
                                typically an HTTP response to send the file to the client.

        Returns:
            None: The report is written directly to the provided response stream.
        """
        data = json.loads(data) if isinstance(data, str) else data
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()
        header_format = workbook.add_format({
            'align': 'center',
            'bold': True,
            'font_size': 20
        })
        subheader_format = workbook.add_format({
            'align': 'center',
            'bold': True,
            'font_size': 14
        })
        label_format = workbook.add_format({
            'align': 'center',
            'bold': True,
            'font_size': 12
        })
        table_header_format = workbook.add_format({
            'align': 'center',
            'bold': True,
            'border': 1,
            'font_size': 11
        })
        table_data_format = workbook.add_format({
            'align': 'left',
            'border': 1,
            'font_size': 10
        })
        flow_name = data.get('data', {}).get('flow_name', 'N/A')
        worksheet.merge_range('B2:I3', flow_name, header_format)
        screens = data.get('data', {}).get('screens', [])
        row = 4
        for screen in screens:
            screen_name = screen.get('screen_name', 'N/A')
            worksheet.write(row, 1, screen_name, subheader_format)
            row += 1
            contents = screen.get('contents', [])
            for content in contents:
                label = content.get('label', 'N/A')
                worksheet.merge_range(row, 2, row, 7, label, label_format)
                row += 1
                worksheet.merge_range(row, 2, row, 3, "Partner",
                                      table_header_format)
                worksheet.merge_range(row, 4, row, 5, "Phone Number",
                                      table_header_format)
                worksheet.merge_range(row, 6, row, 9, "Response",
                                      table_header_format)
                row += 1
                user_responses = content.get('user_responses', [])
                for user_response in user_responses:
                    partner = user_response.get('partner', 'Unknown Partner')
                    whatsapp_number = user_response.get('whatsapp_number',
                                                        'Unknown Number')
                    response_text = user_response.get('user_input', 'N/A')
                    worksheet.merge_range(row, 2, row, 3, partner,
                                          table_data_format)
                    worksheet.merge_range(row, 4, row, 5, whatsapp_number,
                                          table_data_format)
                    worksheet.merge_range(row, 6, row, 9, response_text,
                                          table_data_format)
                    row += 1
                row += 1
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    def send_data(self):
        """
       Collects and prepares data related to user responses, screens, and contents
       for a specific WhatsApp flow and returns it in a structured format.

       This method retrieves all user responses associated with the current WhatsApp
       flow and processes them to count the number of responses, classify them by screen
       and field label, and gather the corresponding user inputs. It also counts the
       number of leads generated based on the responses.

       Returns:
           dict: A dictionary containing:
               - 'flow_name': The name of the WhatsApp flow.
               - 'label_count': The total number of labels with type 'text_answer' or 'selection'.
               - 'response_count': The total number of user responses for the flow.
               - 'leads_generated': The number of CRM leads created from the responses.
               - 'screens': A list of dictionaries representing each screen with its content and user responses.
        """
        user_responses = self.env['flows.user.response'].search(
            [('flows_id', '=', self.id)])
        leads_generated = self.env['crm.lead'].search_count(
            [('response_id', '=', user_responses.ids)])
        user_responses_dict = {}
        for line in user_responses.mapped('flows_user_response_line_ids'):
            screen_id = line.screen_id.id
            field_label = line.field_label
            user_responses_dict.setdefault(screen_id, {}).setdefault(
                field_label, []).append({
                'response_id': line.response_id.id,
                'partner': line.response_id.partner_id.name,
                'partner_id': line.response_id.partner_id.id,
                'whatsapp_number': line.response_id.number,
                'user_input': line.user_input,
            })
        screen_data = []
        label_count = 0
        for screen in self.screen_ids:
            content_data = []
            for content in screen.content_ids:
                if content.content_type in ('text_answer', 'selection'):
                    label_count += 1
                    content_data.append({
                        'type': content.content_type,
                        'selection_type': content.content_selection_type if content.content_type == 'selection' else None,
                        'id': content.id,
                        'label': content.label,
                        'user_responses': user_responses_dict.get(screen.id,
                                                                  {}).get(
                            content.label, []),
                    })
            screen_data.append({
                'screen_name': screen.name,
                'id': screen.id,
                'contents': content_data,
            })
        data = {
            'flow_name': self.name,
            'label_count': label_count,
            'response_count': len(user_responses),
            'leads_generated': leads_generated,
            'screens': screen_data,
        }
        return data

    def action_analysis_flow(self):
        """
        Returns an action to open a custom client-side flow analysis view in fullscreen.

        This method triggers a client-side action that displays the current flow in a
        fullscreen view for analysis.

        Returns:
            dict: The action to display the flow analysis view with context and parameters.
        """
        return {
            "type": "ir.actions.client",
            "tag": "flow_analysis_tag",
            "target": "fullscreen",
            "name": self.name,
            "context": {
                "is_fullscreen": True,
                "active_id": self.id,
            },
            'params': {},
        }

    def _compute_response_done_count(self):
        """
        Computes the count of user responses for the current flow and updates the field.

        This method counts how many user responses are associated with the current flow
        and updates the `response_done_count` field accordingly. If there are no responses,
        the count is set to 0.

        Returns:
            None: This method updates the `response_done_count` field on the current record.
        """
        for record in self:
            response_count = self.env['flows.user.response'].search_count(
                [('flows_id', '=', record.id)])
            if response_count != 0:
                record.response_done_count = response_count
            else:
                record.response_done_count = 0

    @api.depends('name')
    def _compute_flow_name(self):
        """
        Computes and sets a unique flow name based on the flow's name and database UUID.

        This method generates a formatted flow name by removing spaces and converting
        the flow's name to lowercase, then appends the database UUID to make it unique.

        Returns:
            None: This method updates the `flow_name` field on the current record.
        """
        for record in self:
            db_uuid = self.env['ir.config_parameter'].sudo().get_param(
                'database.uuid')
            db_uuid_formatted = db_uuid.replace('-', '')
            name_formatted = str(record.name).strip().replace(" ", "_").lower()
            record.flow_name = f"{name_formatted}_{db_uuid_formatted}"

    def unlink(self):
        """
        Prevent deletion of records in specific states.

        This method overrides the default `unlink` behavior to restrict the
        deletion of records based on their `state` field. Records with states
        'confirmed', 'published', or 'deprecate' cannot be deleted.

        Raises:
            ValidationError: If any record is in 'confirmed', 'published', or
                             'deprecate' state, deletion is blocked and an error
                             message is displayed.

        Returns:
            bool: Result of the `super` call to `unlink`, allowing deletion if
                  all records are in permitted states.
        """
        for record in self:
            if record.state in ('published'):
                raise ValidationError(
                    "You are not allowed to delete records which are  'Published', instead you can 'Deprecate'"
                )
            if record.state == 'confirmed':
                headers = {
                    "Authorization": f"Bearer {self.get_whatsapp_account_details['cloud_token']}",
                }
                response = requests.delete(
                    f"https://graph.facebook.com/v18.0/{self.flow_id}",
                    headers=headers)
                if response.status_code != 200:
                    error = response.json()['error']
                    raise ValidationError(
                        _('%s\n%s\n%s', error['message'],
                          error['error_user_title'],
                          error['error_user_msg']))
        return super(WhatsappFlows, self).unlink()

    @property
    def get_whatsapp_account_details(self):
        """
        Retrieves the WhatsApp account configuration details for the current user.

        This property returns the necessary account details required to send
        WhatsApp messages, including the cloud token, account UID, phone UID,
        and app UID. If any of these details are missing, a ValidationError is raised
        to prompt the user to configure their WhatsApp account.

        Raises:
            ValidationError: If any WhatsApp configuration details are missing.

        Returns:
            dict: A dictionary containing the following keys:
                - 'cloud_token': The WhatsApp cloud token.
                - 'account_uid': The WhatsApp account UID.
                - 'phone_uid': The phone UID associated with WhatsApp.
                - 'app_uid': The app UID for the WhatsApp account.
        """
        if not (self.env.user.token and self.env.user.account_uid and
                self.env.user.phone_uid and self.env.user.app_uid):
            raise ValidationError(
                _('Whatsapp account configuration is required for sending messages. \n '
                  'Go to /Settings/Users & Companies/Users/Whatsapp Account'))
        return {
            'cloud_token': self.env.user.token,
            'account_uid': self.env.user.account_uid,
            'phone_uid': self.env.user.phone_uid,
            'app_uid': self.env.user.app_uid,
        }

    def number_to_word(self, number):
        """
        Converts a numerical value to its word representation in uppercase, with
        hyphens replaced by underscores.
        """
        p = inflect.engine()
        return p.number_to_words(number).upper().replace("-", "_")

    def create_screens(self):
        """
        Generates a JSON configuration for a series of dynamic screens based
        on the screen and content setup in the model.

        This method iterates through the available screens (self.screen_ids)
        and constructs each screen’s layout and components (such as text,
        images, input fields, and selection groups). It accumulates data
        payloads and builds inter-screen navigation based on specified
        screen and content details, creating JSON objects for each screen
        with payload management for passing data between screens.

        Steps include:
            1. Creating screen metadata and layout structure.
            2. Iterating through screen content to define various elements such
               as headings, text inputs, image fields,
               selection options, etc., based on content type.
            3. Setting up payload handling to pass data between screens, storing
               accumulated data for future screens.
            4. Adding navigation or completion actions to each screen footer.

        Returns:
            list: A list of dictionaries, where each dictionary represents a
                  JSON configuration for a screen with  layout, content
                  components, and navigation payloads.
        """
        screens_json = []
        accumulated_data = {}
        for index, screen in enumerate(self.screen_ids, start=1):
            screen_id = f"SCREEN_{self.number_to_word(index)}"
            screen_data = {
                "id": screen_id,
                "title": screen.name,
                "data": accumulated_data.copy(),
                "layout": {
                    "type": "SingleColumnLayout",
                    "children": [
                        {
                            "type": "Form",
                            "name": "form",
                            "children": []
                        }
                    ]
                }
            }
            text_input_counter = 0
            current_screen_payload = {}
            for content in screen.content_ids:
                if content.content_type == 'text':
                    text_type_mapping = {
                        'large_heading': 'TextHeading',
                        'small_heading': 'TextSubheading',
                        'caption': 'TextCaption',
                        'body': 'TextBody'
                    }
                    content_type = text_type_mapping.get(
                        content.content_text_type, 'TextBody')
                    screen_data['layout']['children'][0]['children'].append({
                        "type": content_type,
                        "text": content.text
                    })

                elif content.content_type == 'media':
                    screen_data['layout']['children'][0]['children'].append({
                        "type": "Image",
                        "src": content.image_1920.decode('utf-8'),
                        "height": 400,
                        "scale-type": "contain"
                    })

                elif content.content_type == 'text_answer':
                    text_input_counter += 1
                    input_name = f"{content.shot_answer_type}_{text_input_counter}"
                    answer_type_map = {
                        'short_answer': {
                            "type": "TextInput",
                            "name": input_name,
                            "input-type": content.shot_answer_type
                        },
                        'paragraph': {
                            "type": "TextArea",
                            "name": input_name
                        },
                        'date_picker': {
                            "type": "DatePicker",
                            "name": input_name
                        }
                    }

                    answer_type = answer_type_map.get(
                        content.content_text_answer_type)
                    if answer_type:
                        screen_data['layout']['children'][0]['children'].append(
                            {
                                **answer_type,
                                "label": content.label,
                                "required": content.required,
                                "helper-text": content.instructions if content.instructions else " "
                            })
                        payload_key = f"screen_{index - 1}_TextInput_{text_input_counter - 1}"
                        content.write({
                            'input_key': payload_key
                        })
                        current_screen_payload[
                            payload_key] = f"${{form.{input_name}}}"
                        accumulated_data[payload_key] = {
                            "type": "string",
                            "__example__": "Example"
                        }
                elif content.content_type == 'selection':
                    data_source = [
                        {"id": f"{index}_{item.options}", "title": item.options}
                        for index, item in enumerate(content.option_ids)
                    ]
                    selection_type_map = {
                        'single_choice': "RadioButtonsGroup",
                        'multiple_choice': "CheckboxGroup",
                        'drop_down': "Dropdown"
                    }
                    selection_type = selection_type_map.get(
                        content.content_selection_type)
                    if selection_type:
                        text_input_counter += 1
                        input_name = f"{selection_type}_{text_input_counter}"
                        payload_key = f"screen_{index - 1}_{input_name}_{text_input_counter - 1}"
                        content.write({
                            'input_key': payload_key
                        })
                        screen_data['layout']['children'][0]['children'].append(
                            {
                                "type": selection_type,
                                "label": content.label,
                                "required": content.required,
                                "name": input_name,
                                "data-source": data_source
                            })
                        if selection_type == "CheckboxGroup":
                            current_screen_payload[
                                payload_key] = f"${{form.{input_name}}}"
                            accumulated_data[payload_key] = {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "__example__": []
                            }
                        else:
                            payload_key = f"screen_{index - 1}_{input_name}_{text_input_counter - 1}"
                            current_screen_payload[
                                payload_key] = f"${{form.{input_name}}}"
                            accumulated_data[payload_key] = {
                                "type": "string",
                                "__example__": "Example"
                            }
            full_payload = {}
            full_payload.update(current_screen_payload)
            for key in accumulated_data:
                if key not in current_screen_payload:
                    full_payload[key] = f"${{data.{key}}}"
            if index < len(self.screen_ids):
                screen_data['layout']['children'][0]['children'].append({
                    "type": "Footer",
                    "label": screen.button_name,
                    "on-click-action": {
                        "name": "navigate",
                        "next": {
                            "type": "screen",
                            "name": f"SCREEN_{self.number_to_word(index + 1)}"
                        },
                        "payload": full_payload
                    }
                })
            else:
                screen_data['layout']['children'][0]['children'].append({
                    "type": "Footer",
                    "label": screen.button_name,
                    "on-click-action": {
                        "name": "complete",
                        "payload": full_payload
                    }
                })
                screen_data['terminal'] = True
                screen_data['success'] = True
            screens_json.append(screen_data)
        return screens_json

    def update_created_flow(self):
        """
        Generate and upload a JSON representation of the flow to the WhatsApp API.

        This method:
        1. Creates screens for the flow using the `create_screens` method.
        2. Generates a JSON file containing the flow's screen data.
        3. Uploads the generated JSON file to the WhatsApp API using the flow's unique ID.
        4. Handles errors by raising a `ValidationError` if the API response is not successful.

        Raises:
            ValidationError: If the API response indicates an error during the upload process.

        Returns:
            None
        """
        screens = self.create_screens()
        screen_data = {
            "version": "7.3",
            "screens": screens
        }
        with open("flow.json", "w") as file:
            json.dump(screen_data, file)
        access_token = self.get_whatsapp_account_details['cloud_token']
        url = f'https://graph.facebook.com/v18.0/{self.flow_id}/assets'
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        files = {
            'file': ('flow.json', open('flow.json', 'rb'), 'application/json'),
            'name': (None, 'flow.json'),
            'asset_type': (None, 'FLOW_JSON')
        }
        response = requests.post(url, headers=headers, files=files)
        if response.status_code != 200:
            error = response.json()['error']
            raise ValidationError(
                _('%s\n%s\n%s', error['message'], error['error_user_title'],
                  error['error_user_msg']))

    def action_confirm_flows(self):
        """
        Confirms and submits the WhatsApp flow to the Facebook API.

        This method performs the following steps:
          - Validates that the flow has at least one screen. If no screens are
            found, it raises a `ValidationError`.
          - Retrieves the WhatsApp account details from the user's account
            configuration.
          - Constructs the headers and data for an API request to submit the
            flow to the Facebook API.
          - Sends a POST request to create the flow. If the request fails,
            raises a `ValidationError` with the error details returned by the
            API.
          - On successful submission, updates the `flow_id` with the new flow's
            ID, calls `update_created_flow`, and sets the flow's state to
            'confirmed'.

        Raises:
            ValidationError: If there are no screens in the flow, or if the
                             API request fails with an error.

        Returns:
            None
        """
        if len(self.screen_ids) == 0:
            raise ValidationError(
                _('No screens found in the flow. Please create screens for the flow.'))
        access_token = self.get_whatsapp_account_details['cloud_token']
        account_uid = self.get_whatsapp_account_details['account_uid']
        headers = {
            'Authorization': f"Bearer {access_token}",
            'Content-Type': 'application/json'
        }
        data = {
            "name": self.flow_name,
            "categories": 'OTHER',
        }
        response = requests.post(
            f"https://graph.facebook.com/v18.0/{account_uid}/flows",
            json=data, headers=headers)
        if response.status_code != 200:
            error = response.json()['error']
            if error['code'] == 190:
                raise ValidationError(
                    _('Invalid access token'))
            else:
                raise ValidationError(
                    _('%s\n%s\n%s', error['message'], error['error_user_title'],
                      error['error_user_msg']))
        else:
            self.flow_id = response.json()['id']
            self.update_created_flow()
            self.state = 'confirmed'

    def action_publish_flows(self):
        """
        Publishes the current WhatsApp flow by making an API request to Facebook.

        This method attempts to publish the flow using the Facebook API, updating
        the flow's state to 'published' if successful. If the request fails, it
        logs the error details for debugging and raises a ValidationError to
        inform the user of the issue.

        Steps:
          - Retrieves the access token from the user's WhatsApp account details.
          - Sends a POST request to publish the flow.
          - If the API response status code is not 200, logs the error and raises
            a ValidationError.
          - If successful, sets the flow's state to 'published'.

        Raises:
            None

        Returns:
            None
        """
        access_token = self.get_whatsapp_account_details['cloud_token']
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        response = requests.post(
            f"https://graph.facebook.com/v18.0/{self.flow_id}/publish",
            headers=headers)
        if response.status_code != 200:
            error = response.json()['error']
            raise ValidationError(
                _('%s\n%s', error['message'],
                  error.get('error_user_msg')))
        else:
            self.state = 'published'

    def action_preview_flow(self):
        """
        Generates a preview URL for the WhatsApp flow, allowing the user to view a
        real-time preview of the flow.

        This method retrieves the preview URL for the current flow by making an API
        request to the WhatsApp API with the flow's unique ID. The response includes
        a URL for previewing the flow in a new window.

        Key functionalities:
          - Fetches the cloud token for authorization using the WhatsApp account details.
          - Sends a GET request to the WhatsApp API to retrieve the preview link.
          - Returns an Odoo client action to open the preview in a new window.

        Returns:
            dict: An Odoo client action dictionary that opens a new window to display
                  the flow preview.

        Raises:
            None
        """
        access_token = self.get_whatsapp_account_details['cloud_token']
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        response = requests.get(
            f"https://graph.facebook.com/v18.0/{self.flow_id}?fields=preview.invalidate(false)",
            headers=headers)
        preview_url = response.json().get('preview', {}).get('preview_url', '')
        return {
            "type": "ir.actions.client",
            "tag": "flow_preview_tag",
            "target": "new",
            "name": "Preview",
            "params": {
                "url": preview_url,
            },
        }

    def action_deprecate_flow(self):
        """
        Marks the current WhatsApp flow as deprecated, preventing it from being
        used in future messages.
        """
        access_token = self.get_whatsapp_account_details['cloud_token']
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        response = requests.post(
            f"https://graph.facebook.com/v18.0/{self.flow_id}/deprecate",
            headers=headers)
        if response.status_code != 200:
            error = response.json()['error']
            raise ValidationError(
                _('%s\n%s', error['message'],
                  error['error_user_msg']))
        else:
            self.state = 'deprecate'
            self.active = False

    def action_flows_user_input_completed(self):
        """
        Returns an action to view the user responses for the completed flow.

        This method generates an action to open a window showing the user responses
        associated with the current flow. It updates the context with the flow ID
        to filter the responses specific to the flow.

        Returns:
            dict: The action to open the user responses window, with updated context.

        """
        action = self.env['ir.actions.act_window']._for_xml_id(
            'cyllo_whatsapp_automation.action_view_flows_user_response')
        ctx = dict(self.env.context)
        ctx.update({'search_default_flows_id': self.ids[0]})
        action['context'] = ctx
        return action
    