/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";
import { _t } from "@web/core/l10n/translation";
publicWidget.registry.fieldServicePublicWidget = publicWidget.Widget.extend({
    selector: '.o_portal_fs_service_sidebar',
    events: {
        'click .button_action_done': '_onClickActionDone',
        'click #action_mark_done': '_onClickActionComplete',
        'click #action_start_service': '_onClickActionServiceStart',
    },
    /**
    * init function for getting the this.notification to add notification
    */
    init: function () {
        this.notification = this.bindService("notification");
    },
    /**
    *  function for performing acton done function for field service request
    */
    _onClickActionComplete: function(event){
        jsonrpc("/fs_request/form/action_complete", {
            request_id : event.target.value
        }).then(function(response){
            if(response){
                this.notification.add(_t('Please complete the required steps.'), {
                    type: 'warning',
                    title: _t('User Error'),
                    sticky: false
                })
            }else{
                window.location.reload()
            }
        })
    },
    /**
    *  function for performing start service function for field service request
    */
    _onClickActionServiceStart: function(event){
        jsonrpc("/fs_request/form/action_start", {
            request_id : event.target.value
        }).then(function(){
            window.location.reload()
        })
    },
    /**
    *  function for performing acton start function for field service checklist
    */
     _onClickActionDone: function(event){
        jsonrpc("/fs_request/form/action_done", {
            checkline_id : event.target.id
        }).then(function(){
            window.location.reload()
        })
    }
})
