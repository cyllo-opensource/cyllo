Base Docx Report
=================
This provides a way to Generate DOCX report.

Usage
=====
To use this Module you need to return following action with list of actions to execute:

* Add DOCX button function in module
* data - Add the values for the report
* 'model' - Name of the model where function "get_docx_report" defined
* 'output_format' - formate of the report
* 'report_name' - Name of the Report(blank space is not supported)
.. code-block:: python
        def action_print_docx(self):
            data = {
                'name': self.name,
            }
            return {
                'type': 'ir.actions.report',
                'data': {
                    'model': 'res.partner', # your.model
                    'options': json.dumps(data, default=date_utils.json_default),
                    'output_format': 'docx',
                    'report_name': 'DocsReport',
                },
                'report_type': 'docx',
            }

* DOCX report Function
 In this generate an DOCX report based on the provided data and write it to the response.
.. code-block:: python
    def get_docx_report(self, document, data):
        document.add_paragraph(data['name'])
        return document

Base XLSX Report
=================
This provides a way to Generate XLSX report.

Usage
=====
To use this Module you need to return following action with list of actions to execute:

* Add XLSX button function in module
* data - Add the values for the report
* 'model' - Name of the model
* 'output_format' - formate of the report
* 'report_name' - Name of the Report
.. code-block:: python
    def action_print_xlsx(self):
        data = {
            'name': self.name
        }
        return {
            'type': 'ir.actions.report',
            'data': {
                'model': 'res.partner',
                'options': json.dumps(data, default=date_utils.json_default),
                'output_format': 'xlsx',
                'report_name': 'Excel Report',
            },
            'report_type': 'xlsx',
        }

* XLSX report Function
 In this generate an XLSX report based on the provided data and write it to the response.
.. code-block:: python
    def get_xlsx_report(self, data, response):
        data = json.loads(data)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        sub_heading = workbook.add_format({'align': 'center', 'bold': True, 'font_size': '10px'})
        sheet.write(2, 3, data['name'], sub_heading)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()