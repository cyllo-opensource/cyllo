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
def cyllo_d_uninstall_hook(env):
    """Function to uninstall hooks related to Cyllo Analytics."""
    menu_ids = env['ir.ui.menu'].search([('is_cyllo_analytic_menu', '=', True)])
    for menu in menu_ids:
        menu.action.unlink()
        menu.unlink()
    query = """
        DROP TRIGGER IF EXISTS update_table_name_trigger ON ir_model;
        DROP FUNCTION IF EXISTS update_table_name();
    """
    env.cr.execute(query)

def cyllo_d_post_init_hook(env):
    """Function to execute post initialization hooks for Cyllo Analytics."""
    model_ids = env['ir.model'].search([])
    for rec in model_ids:
        rec.table_name = rec.model.replace('.', '_')
    update_table_name(env)

def update_table_name(env):
    """Function to update table names in the database."""
    # Check if the trigger already exists
    env.cr.execute("""
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'update_table_name_trigger';
    """)
    trigger = env.cr.fetchone()
    if not trigger:
        # If the trigger doesn't exist, create it
        env.cr.execute("""
                       CREATE
                       OR REPLACE FUNCTION update_table_name()
            RETURNS TRIGGER AS $$
            DECLARE
                       model_name TEXT;
                       BEGIN
                IF
                       TG_OP = 'INSERT' THEN
                       SELECT
                       INTO model_name model
                       FROM ir_model
                       WHERE id = NEW.id;
                       model_name
                       := REPLACE(model_name, '.', '_');
                       UPDATE ir_model
                       SET table_name = model_name
                       WHERE id = NEW.id;
                       END IF;
                       RETURN NEW;
                       END;
            $$
                       LANGUAGE plpgsql;

                       CREATE TRIGGER update_table_name_trigger
                           AFTER INSERT
                           ON ir_model
                           FOR EACH ROW
                           EXECUTE PROCEDURE update_table_name();
                       """)
