/** @odoo-module **/
import {getFixture,click} from "@web/../tests/helpers/utils";
import {makeView,setupViewRegistries} from "@web/../tests/views/helpers";
let target;
let serverData;
/**
 * Test module for document file
 */
QUnit.module("CylloDocumentFileViews", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                'document.file': {
                    fields: {
                        name: {
                            string: "Name",
                            type: "char"
                        },
                        date: {
                            string: "Date",
                            type: "date"
                        },
                        attachment: {
                            string: "Attachment",
                            type: "char"
                        },
                    },
                    records: [{
                        id: 1,
                        name: "Doc1",
                        date: "2023-11-15",
                        attachment: "file.txt",
                    }, ],
                },
            },
        };
        setupViewRegistries();
    });
    QUnit.module("CylloDocuments");
    QUnit.test(
        "Renders Kanban view with document elements",
        async function(assert) {
            const kanbanView = await makeView({
                type: "kanban",
                resModel: "document.file",
                serverData,
                arch: `
                    <kanban>
                        <field name="name"/>
                        <field name="date"/>
                        <field name="attachment" filename="name"/>
                        <templates>
                    <t t-name="kanban-box">
                    <div class="kanban_document">
                                <div class="document_table">
                                    <table class="kanban_table">
                                        <tr>
                                            <td><field name="name"/></td>
                                        </tr>
                                        <tr>
                                            <td><field name="date"/></td>
                                        </tr>
                                        <tr>
                                            <td><field name="attachment"/></td>
                                        </tr>
                                    </table>
                                </div>
                             </div>
                            </t>
                        </templates>
                    </kanban>`,
            });
            const kanbanElements = target.querySelectorAll('.kanban_document');
            const documentName = kanbanElements[0].querySelector('.document_table tr:nth-child(1) td').textContent.trim();
            const documentDate = kanbanElements[0].querySelector('.document_table tr:nth-child(2) td').textContent.trim();
            const documentAttachment = kanbanElements[0].querySelector('.document_table tr:nth-child(3) td').textContent.trim();
            assert.strictEqual(documentName, "Doc1", "Document name matches");
            assert.strictEqual(documentDate, "11/15/2023", "Document date matches");
            assert.strictEqual(documentAttachment, "file.txt", "Document attachment matches");
        }
    );
});