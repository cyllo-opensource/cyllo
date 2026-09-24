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
import base64
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WhatsappFlowsScreenContents(models.Model):
    """
    Model representing various content elements for a WhatsApp flow screen.

    This model defines the types of content that can be included in each screen
    of a WhatsApp flow, including text, media, answers, and selection options.
    """
    _name = 'whatsapp.flows.screen.contents'
    _description = 'WhatsApp Flow Screen Contents'

    screen_id = fields.Many2one(
        comodel_name='whatsapp.flows.screens',
        string='Flow Screen',
        help='The specific flow screen to which this content belongs.'
    )
    content_type = fields.Selection(
        [('text', 'Text'),
         ('media', 'Media'),
         ('text_answer', 'Text Answer'),
         ('selection', 'Selection'), ],
        string='Select Content Type',
        default='text',
        required=True,
        help='Specify the type of content for this screen, such as text, media,'
             ' a text answer, or a selection.'
    )
    content_text_type = fields.Selection(
        [('large_heading', 'Large Heading'),
         ('small_heading', 'Small Heading'),
         ('caption', 'Caption'),
         ('body', 'Body'), ],
        default="large_heading",
        string='Text type',
        help='Choose the text style, such as Large Heading, Small Heading, '
             'Caption, or Body.'
    )
    text = fields.Text(
        string='Text Content',
        help='Enter the text to be displayed if the content type is set to Text.'
    )
    content_text_answer_type = fields.Selection(
        [('short_answer', 'Short Answer'),
         ('paragraph', 'Paragraph'),
         ('date_picker', 'Date picker')],
        default="short_answer",
        string='Text Answer Type',
        help='Specify the format for the text answer, such as a short answer, '
             'paragraph, or date picker.'
    )
    content_selection_type = fields.Selection(
        [('single_choice', 'Single Choice'),
         ('multiple_choice', 'Multiple Choice'),
         ('drop_down', 'Drop Down')],
        string='Selection type',
        default='single_choice',
        help='Select the type of selection input, such as Single Choice,'
             ' Multiple Choice, or Drop Down.'

    )
    image_1920 = fields.Image(
        string='Image',
        help='Upload an image if the content type is set to Media.'
    )
    shot_answer_type = fields.Selection(
        [('text', 'Text'),
         ('password', 'Password'),
         ('email', 'Email'),
         ('number', 'Number'),
         ('passcode', 'Passcode'),
         ('phone', 'Phone')],
        default='text',
        string='Answer Input Type',
        help='Choose the input type for answers, such as text, password, email,'
             ' number, passcode or phone.'
    )
    label = fields.Char(
        string='label',
        help='Provide a label for the content field, describing its purpose or'
             ' content.'
    )
    input_key = fields.Char(
        string='Input Key',
        help='Key for the content field'
    )
    instructions = fields.Char(
        string='Instructions',
        help='Add any instructions to guide users on how to interact with this'
             ' content field.'
    )
    required = fields.Boolean(
        string='Required',
        default=True,
        help='Indicate whether this content field is required. '
             'If checked, the user must complete this field before proceeding.'
    )
    option_ids = fields.One2many(
        comodel_name='screen.content.options',
        inverse_name='content_id',
        string="Selection Options",
        help='List of selectable choices for this content if the content type '
             'is set to Selection.'
    )
    user_id = fields.Many2one(
        string='Responsible User',
        comodel_name='res.users',
        default=lambda self: self.env.user,
        help="User responsible for managing this content."
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
        string='Associated Company',
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        help="Link this content to a specific product, if applicable. This is "
             "used if the content is tied to a product in the flow."
    )

    @api.constrains('label', 'screen_id', 'content_type', 'option_ids',
                    'image_1920')
    def _check_content_validations(self):
        """
        Validate the following conditions:
        1. Ensure that the label is unique within the same screen.
        2. Ensure that 'selection' type content has at least two options.
        3. Ensure that the image size does not exceed 300KB.

        Raises:
            ValidationError: If any of the above conditions are not met.
        """
        for record in self:
            if record.content_type == 'selection' and len(
                    record.option_ids) < 2:
                raise ValidationError(
                    f"The content '{record.label}' of type 'Selection' "
                    f"in the screen '{record.screen_id.name}' "
                    f"must have at least two options."
                )
            if record.content_type == 'media' and record.image_1920:
                image_size = len(base64.b64decode(record.image_1920))
                if image_size > 300 * 1024:
                    raise ValidationError(
                        f"The image size for content in screen "
                        f"'{record.screen_id.name}' exceeds 300KB."
                    )
