/** @odoo-module **/
import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
let target;
let serverData;
/**
 * Test module for Document Template
 */
QUnit.module("CylloDocumentTemplate",{
    beforeEach:function(){
        target = getFixture();
        serverData={
            models:{
                'res.users': {
                    fields: {
                        display_name: { string: 'Name', type: 'char' },
                    },
                    records: [
                        { id: 1, name: 'Mario' },
                        { id: 2, name: 'Luigi' },
                    ],
                },
                'document.request.template':{
                    fields:{
                        name:{string:"Name",type:"char"},
                        user_ids:{string:"User",type:"many2many", relation: 'res.users' },
                    },
                    records:[
                        {
                            id:1,
                            name:"Test Template",
                            user_ids:[1,2]
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
                        <field name="user_ids" widget="many2many_tags"/>
                    </group>
                  </form>`,
            serverData,
            type: "form",
            resModel: 'document.request.template',
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
        // Check if user names are displayed instead of IDs
        assert.strictEqual(document.querySelector(".o_field_char").innerText, 'Test Template', 'Document displayed correctly');
    });
})