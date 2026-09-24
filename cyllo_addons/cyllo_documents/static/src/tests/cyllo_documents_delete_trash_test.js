/** @odoo-module **/
import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
let target;
let serverData;
/**
 * Test module for document delete
 */
QUnit.module("CylloDocumentDelete",{
    beforeEach:function(){
        target = getFixture();
        serverData = {
            models:{
                'document.file':{
                    fields:{
                        name:{string:'Name',type:'char'}
                    },
                    records:[
                        {id:1,name:"Doc1"},
                    ],
                },
                'document.delete.trash':{
                    fields:{
                        document_file_id:{string:'Document',type:'many2one',relation:'document.file'},
                    },
                    records:[
                        {id:1,document_file_id:1}
                    ]
                }
            },
            views:{}
        }
        this.testFormView = {
            arch:`<form>
                    <group>
                        <field name="document_file_id"/>
                    </group>
                  </form>`  ,
            serverData,
            type: "form",
            resModel: 'document.delete.trash',
        }
        setupViewRegistries();
    },
},function(){
    QUnit.test("Creates a document delete template",async function (assert){
        const form = await makeView({
            ...this.testFormView,
            resId: 1,
        })
        assert.strictEqual(document.querySelector(".o_field_many2one").innerText, 'Doc1', 'New delete document');
    })
})