/** @odoo-module **/
import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
let target;
let serverData;
/**
 * Test module for CylloDocumentWorkspace
 */
QUnit.module("CylloDocumentWorkspace",{
    beforeEach:function(){
        target = getFixture();
        serverData={
            models:{
                'res.company': {
                fields: {
                    name: { string: 'Name', type: 'char' },
                },
                records: [
                    { id: 1, name: 'New Company' }
                ]
            },
            'document.workspace': {
                fields: {
                    name: { string: 'Name', type: 'char' },
                    company_id: { string: 'Company', type: 'many2one', relation: 'res.company' }
                },
                records: [
                    {
                        id: 1,
                        name: "Workspace1",
                        company_id: 1
                    }
                ]
            }
            },
            views:{}
        }
        this.testFormView = {
            arch:`<form>
                    <group>
                        <field name="name"/>
                        <field name="company_id"/>
                    </group>
                  </form>`,
            serverData,
            type: "form",
            resModel: 'document.workspace',
        }
        setupViewRegistries();
    },
},function () {
    QUnit.test("Creates a document template", async function (assert) {
        // Get the form view with server data
        const form = await makeView({
            ...this.testFormView,
            resId: 1,
        });
        assert.strictEqual(document.querySelector(".o_field_char").innerText, 'Workspace1', 'New Workspace');
        assert.strictEqual(document.querySelector(".o_form_uri").innerText, 'New Company', 'New Workspace company');

    });
})