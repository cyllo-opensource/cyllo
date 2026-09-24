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
import requests
import xml.etree.ElementTree as ET
from datetime import date, datetime

from odoo import _, fields, models, release
from odoo.exceptions import UserError, ValidationError


class DeliveryCarrier(models.Model):
    """
        This class inherits 'delivery.carrier' model for using delivery carrier
        functionality
    """
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(selection_add=[('dhl', 'DHL')],
                                     ondelete={'dhl': 'set default'})
    service_type = fields.Selection(selection=[
        ('0', '0 - LOGISTIC SERVICES'),
        ('1', '1 - DOMESTIC EXPRESS 12.00 '),
        ('2', '2 - B2C'),
        ('3', '3 - B2C'),
        ('4', '4 - JET LINE'),
        ('5', '5 - SPRINT LINE'),
        ('6', '6 - SECURE LINE'),
        ('7', '7 - EXPRESS EASY'),
        ('8', '8 - EXPRESS EASY'),
        ('9', '9 - EURO PACK'),
        ('A', 'A - AUTO REVERSALS'),
        ('B', 'B - BREAK BULK EXPRESS'),
        ('C', 'C - MEDICAL EXPRESS'),
        ('D', 'D - EXPRESS WORLDWIDE'),
        ('E', 'E - EXPRESS 9.00'),
        ('F', 'F - FREIGHT WORLDWIDE'),
        ('G', 'G - DOMESTIC ECONOMY SELECT'),
        ('H', 'H - ECONOMY SELECT'),
        ('I', 'I - BREAK BULK ECONOMY SELECT'),
        ('J', 'J - JUMBO BOX'),
        ('K', 'K - EXPRESS 9.00'),
        ('L', 'L- EXPRESS 10:30'),
        ('M', 'M - EXPRESS 10:30'),
        ('N', 'N - DOMESTIC EXPRESS'),
        ('O', 'O - DOM EXPRESS 10:30'),
        ('P', 'P - EXPRESS WORLDWIDE'),
        ('Q', 'Q - MEDICAL EXPRESS'),
        ('R', 'R - GLOBAL MAIL EXPRESS'),
        ('S', 'S - SAME DAY'),
        ('T', 'T - EXPRESS 12.00'),
        ('U', 'U - EXPRESS WORLDWIDE'),
        ('V', 'V - EURO PACK'),
        ('W', 'W - ECONOMY SELECT'),
        ('X', 'X - EXPRESS ENVELOP'),
        ('Y', 'Y - EXPRESS 12.00'),
        ('Z', 'Z - DESTINATION CHARGES')], help="Service Types in DHL")
    weight_uom = fields.Selection(selection=[('KG', 'KG'), ('P', 'P')],
                                  string="Unit of Measure",
                                  help="Package Unit of Measure")
    region = fields.Selection(selection=[('asiapacific', 'Asia Pacific'),
                                         ('america', 'America'),
                                         ('europe', 'Europe')],
                              help="Region codes for Shipping")
    label_template = fields.Selection(selection=[('label', '8*4_A4_PDF'), ],
                                      help="Label Template for Shipping Label")
    label_format = fields.Selection(
        selection=[('PDF', 'PDF'), ('ZPL2', 'ZPL2'), ],
        help="Label Format for template")
    site_id = fields.Char(string="DHL Site ID", help="DHL Customer's site id")
    password = fields.Char(string="DHL Password", help="DHL Customer Password")
    account_no = fields.Integer(string="DHL Account Number",
                                help="Account number of DHL Customer")
    package_type_id = fields.Many2one("stock.package.type",
                                      string="Package Type",
                                      help="Package Types available in DHL")
    dimension_unit = fields.Selection(selection=[('I', 'I'), ('CM', 'CM')],
                                      string="Dimensional Unit",
                                      help="Dimensional Unit available in dhl")
    insured_value = fields.Float(help="Insurance value in DHL")
    dutiable = fields.Boolean(help="Check package is dutiable or not")

    def dhl_rate_shipment(self, order):
        """
            This function calculates the shipping rate for a given order
            using DHL's services.
        """
        if not self.account_no:
            raise UserError(_("Account Number is Missing"))
        if not self.site_id:
            raise UserError(_("Site ID is Missing"))
        if not self.password:
            raise UserError(_("Password is Missing"))
        weight = 0
        for rec in order.order_line:
            weight = weight + (rec.product_uom_qty * rec.product_id.weight)
        xml_request = f'<?xml version="1.0" encoding="utf-8"?>' \
                      f'<ns0:DCTRequest xmlns:ns0="http://www.dhl.com" schemaVersion="2.0">' \
                      f'<GetQuote>' \
                      f'    <Request>' \
                      f'        <ServiceHeader>' \
                      f'            <MessageTime>{datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")}</MessageTime>' \
                      f'            <MessageReference>ref:{datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")}' \
                      f'</MessageReference>' \
                      f'            <SiteID>{self.site_id}</SiteID>' \
                      f'            <Password>{self.password}</Password>' \
                      f'        </ServiceHeader>' \
                      f'        <MetaData>' \
                      f'            <SoftwareName>{release.product_name}</SoftwareName>' \
                      f'            <SoftwareVersion>{release.series}</SoftwareVersion>' \
                      f'        </MetaData>' \
                      f'    </Request>' \
                      f'    <From>' \
                      f'        <CountryCode>{self.env.company.country_code}</CountryCode>' \
                      f'        <Postalcode>{self.env.company.zip}</Postalcode>' \
                      f'        <City>{self.env.company.city}</City>' \
                      f'    </From>' \
                      f'    <BkgDetails>' \
                      f'        <PaymentCountryCode>{order.warehouse_id.partner_id.country_code}' \
                      f'</PaymentCountryCode>' \
                      f'        <Date>{date.today()}</Date>' \
                      f'        <ReadyTime>PT1H2M</ReadyTime>' \
                      f'        <DimensionUnit>{self.dimension_unit}</DimensionUnit>' \
                      f'        <WeightUnit>{self.weight_uom}</WeightUnit>' \
                      f'        <Pieces>' \
                      f'            <Piece>' \
                      f'                <PieceID>0</PieceID>' \
                      f'                <PackageTypeCode>{self.package_type_id.barcode}</PackageTypeCode>' \
                      f'                <Height>{self.package_type_id.height}</Height>' \
                      f'                <Depth>{self.package_type_id.packaging_length}</Depth>' \
                      f'                <Width>{self.package_type_id.width}</Width>' \
                      f'                <Weight>{weight}</Weight>' \
                      f'            </Piece>' \
                      f'        </Pieces>' \
                      f'        <PaymentAccountNumber>{self.account_no}</PaymentAccountNumber>' \
                      f'        <IsDutiable>{"N" if self.dutiable is False else "Y"}</IsDutiable>' \
                      f'        <NetworkTypeCode>AL</NetworkTypeCode>' \
                      f'        <InsuredValue>0</InsuredValue>' \
                      f'        <InsuredCurrency>{self.env.company.currency_id.name}</InsuredCurrency>' \
                      f'    </BkgDetails>' \
                      f'    <To>' \
                      f'        <CountryCode>{order.partner_shipping_id.country_code}</CountryCode>' \
                      f'        <Postalcode>{order.partner_shipping_id.zip}</Postalcode>' \
                      f'        <City>{order.partner_shipping_id.city}</City>' \
                      f'    </To>' \
                      f'</GetQuote>' \
                      f'</ns0:DCTRequest>'

        url = "https://xmlpitest-ea.dhl.com//XMLShippingServlet/DCTRequest"
        headers = {
            'content-type': "application/xml",
            'Content-Length': "0"
        }
        response = requests.post(url, data=xml_request, headers=headers)
        qtd_shp_elements = ET.fromstring(response.text).findall(".//QtdShp")
        vals = {}
        flag = False
        for qtd_shp_element in qtd_shp_elements:
            global_product_code = qtd_shp_element.find("GlobalProductCode")
            shipping_charge = qtd_shp_element.find("ShippingCharge")
            if self.service_type == global_product_code.text.strip():
                vals['success'] = True
                vals['price'] = shipping_charge.text.strip()
                vals['carrier_price'] = vals['price']
                vals['warning_message'] = "Successfully added the DHL Shipping"
                return vals
        if not flag:
            raise UserError(_("There is no service available"))

    def dhl_send_shipping(self, pickings):
        """
           Send a shipping request to DHL for a list of pickings.
           This method creates a shipping order for each picking in the
           provided list and sends it to DHL.
        """
        res = []
        shipping_price = self.create_order(pickings)
        res = res + [{
            'exact_price': float(shipping_price),
            'tracking_number': False
        }]
        return res

    def create_order(self, pickings):
        """
           This function is responsible for creating an order with DHL.
           It should be used when you need to send shipments through DHL.
        """
        shipping_request = ''
        price = 0
        weight = 0
        for rec in pickings.move_line_ids:
            price = price + (rec.quantity * rec.product_id.list_price)
            weight = weight + (rec.quantity * rec.product_id.weight)
        shipping_request = """<req:ShipmentRequest schemaVersion="10.0" xmlns:req="http://www.dhl.com">
                                <Request>
                                    <ServiceHeader>
                                        <MessageTime>{message_time}</MessageTime>
                                        <MessageReference>{message_reference}</MessageReference>
                                        <SiteID>{site_id}</SiteID>
                                        <Password>{password}</Password>
                                    </ServiceHeader>
                                    <MetaData>
                                        <SoftwareName>{software_name}</SoftwareName>
                                        <SoftwareVersion>{software_series}</SoftwareVersion>
                                    </MetaData>
                                    </Request>
                                    <RegionCode>AM</RegionCode>
                                    <RequestedPickupTime>Y</RequestedPickupTime>
                                    <LanguageCode>en</LanguageCode>
                                    <Billing>
                                        <ShipperAccountNumber>{shipper_account_number}</ShipperAccountNumber>
                                        <ShippingPaymentType>S</ShippingPaymentType>
                                        <BillingAccountNumber>None</BillingAccountNumber>
                                    </Billing>
                                    <Consignee>
                                        <CompanyName>{company_name}</CompanyName>
                                        <AddressLine1>{address_line1}</AddressLine1>
                                        <AddressLine2>None</AddressLine2>
                                        <AddressLine3>None</AddressLine3>
                                        <City>{city}</City>
                                        <PostalCode>{postal_code}</PostalCode>
                                        <CountryCode>{country_code}</CountryCode>
                                        <CountryName>{country_name}</CountryName>
                                        <Contact>
                                            <PersonName>{person_name}</PersonName>
                                            <PhoneNumber>35318746881</PhoneNumber>
                                            <Email>{email}</Email>
                                            <MobilePhoneNumber>None</MobilePhoneNumber>
                                        </Contact>
                                        <StreetName>None</StreetName>
                                        <BuildingName>None</BuildingName>
                                        <StreetNumber>None</StreetNumber>
                                        <RegistrationNumbers>
                                            <RegistrationNumber>
                                                <Number>None</Number>
                                                <NumberTypeCode>RGP</NumberTypeCode>
                                                <NumberIssuerCountryCode>{number_issuer_country_code}</NumberIssuerCountryCode>
                                            </RegistrationNumber>
                                        </RegistrationNumbers>
                                    </Consignee>
                                    <Dutiable>
                                        <DeclaredValue>72.025</DeclaredValue>
                                        <DeclaredCurrency>EUR</DeclaredCurrency>
                                        <ShipperEIN>ShipperEIN</ShipperEIN>
                                        <TermsOfTrade>DAP</TermsOfTrade>
                                    </Dutiable>
                                    <UseDHLInvoice>Y</UseDHLInvoice>
                                    <DHLInvoiceLanguageCode>en</DHLInvoiceLanguageCode>
                                    <DHLInvoiceType>CMI</DHLInvoiceType>
                                    <ExportDeclaration>
                                        <InvoiceNumber>MyDHLAPI - INV-001</InvoiceNumber>
                                        <InvoiceDate>{invoice_date}</InvoiceDate>
                                        <ExportLineItem>
                                            <LineNumber>1</LineNumber>
                                            <Quantity>1</Quantity>
                                            <QuantityUnit>PCS</QuantityUnit>
                                            <Description>{description}</Description>
                                            <Value>{value}</Value>
                                            <IsDomestic>Y</IsDomestic>
                                            <CommodityCode>123</CommodityCode>
                                            <Weight>
                                                <Weight>{weight}</Weight>
                                                <WeightUnit>K</WeightUnit>
                                            </Weight>
                                            <GrossWeight>
                                                <Weight>{weight}</Weight>
                                                <WeightUnit>K</WeightUnit>
                                            </GrossWeight>
                                            <ManufactureCountryCode>TH</ManufactureCountryCode>
                                            <ImportCommodityCode>123</ImportCommodityCode>
                                            <ItemReferences>
                                                <ItemReference>
                                                    <ItemReferenceType>AFE</ItemReferenceType>
                                                    <ItemReferenceNumber>AFE-1299210554413</ItemReferenceNumber>
                                                </ItemReference>
                                            </ItemReferences>
                                            <CustomsPaperworks>
                                                <CustomsPaperwork>
                                                    <CustomsPaperworkType>INV</CustomsPaperworkType>
                                                    <CustomsPaperworkID>MyDHLAPI - LN#1-CUSDOC-001</CustomsPaperworkID>
                                                </CustomsPaperwork>
                                            </CustomsPaperworks>
                                        </ExportLineItem>
                                        <InvoiceInstructions>This is invoice instruction</InvoiceInstructions>
                                        <CustomerDataTextEntries>
                                            <CustomerDataTextEntry>
                                                <CustomerDataTextNumber>1</CustomerDataTextNumber>
                                                <CustomerDataText>Customer Data Text Line - First</CustomerDataText>
                                            </CustomerDataTextEntry>
                                        </CustomerDataTextEntries>
                                        <PlaceOfIncoterm>DUBLIN PORT</PlaceOfIncoterm>
                                        <ShipmentPurpose>COMMERCIAL</ShipmentPurpose>
                                        <CustomsDocuments>
                                            <CustomsDocument>
                                                <CustomsDocumentType>INV</CustomsDocumentType>
                                                <CustomsDocumentID>MyDHLAPI - CUSDOC-001</CustomsDocumentID>
                                            </CustomsDocument>
                                        </CustomsDocuments>
                                        <InvoiceTotalNetWeight>7.800</InvoiceTotalNetWeight>
                                        <InvoiceTotalGrossWeight>8.250</InvoiceTotalGrossWeight>
                                        <InvoiceReferences>
                                            <InvoiceReference>
                                                <InvoiceReferenceType>OID</InvoiceReferenceType>
                                                <InvoiceReferenceNumber>MyDHLAPI - OIDREF-002</InvoiceReferenceNumber>
                                            </InvoiceReference>
                                        </InvoiceReferences>
                                    </ExportDeclaration>
                                    <ShipmentDetails>
                                        <Pieces>
                                            <Piece>
                                                <PieceID>0</PieceID>
                                                <PackageType>BOX</PackageType>
                                                <Weight>{weight}</Weight>
                                                <Width>{width}</Width>
                                                <Height>{height}</Height>
                                                <Depth>{depth}</Depth>
                                            </Piece>
                                        </Pieces>
                                        <WeightUnit>{weight_unit}</WeightUnit>
                                        <GlobalProductCode>{global_product_code}</GlobalProductCode>
                                        <LocalProductCode>{local_product_code}</LocalProductCode>
                                        <Date>{date}</Date>
                                        <Contents>FST-Test_CI-Mask_1p24-Schema10</Contents>
                                        <DimensionUnit>{dimension_unit}</DimensionUnit>
                                        <PackageType>BOX</PackageType>
                                        <IsDutiable>{dutiable}</IsDutiable>
                                        <CurrencyCode>{currency_code}</CurrencyCode>
                                    </ShipmentDetails>
                                    <Shipper>
                                        <ShipperID>{shipper_account_number}</ShipperID>
                                        <CompanyName>{company_name_origin}</CompanyName>
                                        <AddressLine1>{AddressLine1}</AddressLine1>
                                        <AddressLine2>{AddressLine2}</AddressLine2>
                                        <AddressLine3>None</AddressLine3>
                                        <City>{city_origin}</City>
                                        <PostalCode>{postal_code_origin}</PostalCode>
                                        <CountryCode>{country_code_origin}</CountryCode>
                                        <CountryName>{country_name_origin}</CountryName>
                                        <Contact>
                                            <PersonName>{person_name_origin}</PersonName>
                                            <PhoneNumber>None</PhoneNumber>
                                            <PhoneExtension>None</PhoneExtension>
                                            <FaxNumber>None</FaxNumber>
                                            <Telex>None</Telex>
                                            <Email>{email_origin}</Email>
                                            <MobilePhoneNumber>None</MobilePhoneNumber>
                                        </Contact>
                                        <StreetName>None</StreetName>
                                        <BuildingName>None</BuildingName>
                                        <StreetNumber>None</StreetNumber>
                                    </Shipper>
                                     <LabelImageFormat>{label_image_format}</LabelImageFormat>
                                </req:ShipmentRequest>""".format(
            message_time=datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f'),
            message_reference='ref:' + datetime.now().strftime(
                '%Y-%m-%dT%H:%M:%S.%f'),
            software_name=release.product_name,
            software_series=release.series,
            site_id=self.site_id,
            password=self.password,
            region_code=self.region,
            shipper_account_number=self.account_no,
            company_name=pickings.partner_id.name,
            address_line1=pickings.partner_id.street,
            city=pickings.partner_id.city,
            postal_code=pickings.partner_id.zip,
            country_code=pickings.partner_id.country_id.code,
            country_name=pickings.partner_id.country_id.name,
            person_name=pickings.picking_type_id.warehouse_id.company_id.name,
            email=pickings.picking_type_id.warehouse_id.company_id.email,
            number_issuer_country_code=pickings.picking_type_id.warehouse_id.company_id.country_id.code,
            shipper_ID=self.account_no,
            invoice_date=date.today(),
            quantity_unit="PCS",
            description=pickings.name,
            value=price,
            weight=weight,
            package_type=self.package_type_id.shipper_package_code,
            width=self.package_type_id.width,
            height=self.package_type_id.height,
            depth=self.package_type_id.packaging_length,
            global_product_code=self.service_type,
            local_product_code=self.service_type,
            date=date.today(),
            currency_code=pickings.picking_type_id.warehouse_id.company_id.currency_id.name,
            city_origin=pickings.picking_type_id.warehouse_id.company_id.city,
            company_name_origin=pickings.picking_type_id.warehouse_id.company_id.name,
            AddressLine1=pickings.picking_type_id.warehouse_id.company_id.street,
            AddressLine2=pickings.picking_type_id.warehouse_id.company_id.street2,
            postal_code_origin=pickings.picking_type_id.warehouse_id.company_id.zip,
            country_code_origin=pickings.picking_type_id.warehouse_id.company_id.country_id.code,
            country_name_origin=pickings.picking_type_id.warehouse_id.company_id.country_id.name,
            person_name_origin=pickings.picking_type_id.warehouse_id.company_id.name,
            email_origin=pickings.picking_type_id.warehouse_id.company_id.email,
            label_image_format=self.label_format,
            dimension_unit="C" if self.dimension_unit == "CM" else "I",
            weight_unit="K" if self.weight_uom == "KG" else "P",
            dutiable="N" if self.dutiable == False else "Y"
        )
        url = "https://xmlpitest-ea.dhl.com//XMLShippingServlet/shipment-validation"
        headers = {
            'content-type': "application/xml",
            'Content-Length': "0"
        }
        response = requests.post(url, data=shipping_request,
                                 headers=headers)
        if '<ActionStatus>Error</ActionStatus>' in response.text:
            raise ValidationError(
                _("DHL Error: Validation Failure. Site ID is wrong.")
            )
        shipping_price = ET.fromstring(response.text).find(
            "ShippingCharge").text
        tracking_number = ET.fromstring(response.text).find(
            "AirwayBillNumber").text
        label = ET.fromstring(response.text).find(
            "LabelImage/OutputImage").text
        pickings.carrier_tracking_ref = tracking_number
        label_attachment = self.env['ir.attachment'].sudo().create({
            'name': 'DHL Shipping Label.pdf',
            'type': 'binary',
            'mimetype': 'application/pdf',
            'datas': label,
            'res_model': 'stock.picking',
            'res_id': pickings.id
        })
        pickings.message_post(
            body="Created Shipment in DHL. Your tracking number is: %s" % tracking_number,
            attachment_ids=[label_attachment.id])
        return shipping_price

    def dhl_get_tracking_link(self, picking):
        """
           This function is used to generate a DHL tracking link for a given
           order's tracking number. It takes the picking parameter, which
           should contain the tracking number for the order, and generates a
           DHL tracking link using the tracking number.
        """
        return 'http://www.dhl.com/en/express/tracking.html?AWB=%s' % picking.carrier_tracking_ref
