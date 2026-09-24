/** @odoo-module **/
import {ActivityMenu} from '@mail/core/web/activity_menu'

const nameShow = { type: Boolean, optional: true };
ActivityMenu.props = {...ActivityMenu.props, nameShow}