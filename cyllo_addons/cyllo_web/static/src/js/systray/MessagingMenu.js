/** @odoo-module **/
import {MessagingMenu} from '@mail/core/web/messaging_menu'

const nameShow = {type: Boolean, optional: true};
MessagingMenu.props = {...MessagingMenu.props, nameShow}