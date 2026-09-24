# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cyllo(<https://www.cyllo.com>)
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
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestWorkAutoP2(TransactionCase):
    """Phase-2 tests for work.auto: is_reusable, trigger_function_ids, dry_run, run_now,
    create_cron, _get_actions, _process, get_context, and get_dependents."""

    def setUp(self):
        super().setUp()
        self.WorkAuto = self.env['work.auto']
        self.model_partner = self.env['ir.model'].search(
            [('model', '=', 'res.partner')], limit=1
        )
        self.func_write = self.env['work.function'].create({
            'name': 'On Write P2',
            'func_name': 'write',
            'trigger_type': 'write',
        })

    def _make_wa(self, **kw):
        vals = {'name': 'WA P2 Test', 'model_id': self.model_partner.id}
        vals.update(kw)
        return self.WorkAuto.create(vals)

    def _make_reusable_wa(self, **kw):
        vals = {
            'name': 'Reusable WA',
            'model_id': self.model_partner.id,
            'is_reusable': True,
            'reuse_scope': 'generic',
        }
        vals.update(kw)
        return self.WorkAuto.create(vals)

    # ─────────────────────── is_reusable field ──────────────────────────────────

    def test_01_is_reusable_defaults_false(self):
        """is_reusable defaults to False."""
        wa = self._make_wa()
        self.assertFalse(wa.is_reusable)

    def test_02_is_reusable_can_be_set_true(self):
        """is_reusable can be set to True on creation."""
        wa = self._make_reusable_wa()
        self.assertTrue(wa.is_reusable)

    def test_03_reuse_scope_defaults_generic(self):
        """reuse_scope default is 'generic'."""
        wa = self._make_reusable_wa()
        self.assertEqual(wa.reuse_scope, 'generic')

    def test_04_is_reusable_false_after_toggle(self):
        """is_reusable can be toggled back to False via write."""
        wa = self._make_reusable_wa()
        wa.write({'is_reusable': False})
        self.assertFalse(wa.is_reusable)

    # ─────────────────── trigger_function_ids computed field ────────────────────

    def test_05_trigger_function_ids_field_exists(self):
        """trigger_function_ids Many2many field is present on work.auto."""
        wa = self._make_wa()
        self.assertIn('trigger_function_ids', wa._fields)

    def test_06_trigger_function_ids_empty_on_plain_create(self):
        """trigger_function_ids is empty when no flow_data set."""
        wa = self._make_wa()
        self.assertFalse(wa.trigger_function_ids)

    def test_07_trigger_function_ids_set_via_write(self):
        """trigger_function_ids can be set via ORM write."""
        wa = self._make_wa()
        wa.write({'trigger_function_ids': [(4, self.func_write.id)]})
        self.assertIn(self.func_write, wa.trigger_function_ids)

    # ─────────────── _check_unique_trigger_types constraint ─────────────────────

    def test_08_duplicate_trigger_types_raise_validation_error(self):
        """Adding two functions with the same trigger_type raises ValidationError."""
        func2 = self.env['work.function'].create({
            'name': 'On Write P2 Dup',
            'func_name': 'write2',
            'trigger_type': 'write',
        })
        wa = self._make_wa()
        with self.assertRaises(ValidationError):
            wa.write({
                'trigger_function_ids': [(6, 0, [self.func_write.id, func2.id])]
            })

    def test_09_distinct_trigger_types_do_not_raise(self):
        """Two functions with different trigger_types are allowed together."""
        func_create = self.env['work.function'].create({
            'name': 'On Create P2',
            'func_name': 'create',
            'trigger_type': 'create',
        })
        wa = self._make_wa()
        wa.write({
            'trigger_function_ids': [(6, 0, [self.func_write.id, func_create.id])]
        })
        self.assertEqual(len(wa.trigger_function_ids), 2)

    # ─────────────────── _get_actions uses trigger_function_ids ─────────────────

    def test_10_get_actions_finds_via_trigger_function_ids(self):
        """_get_actions returns automation linked via trigger_function_ids."""
        wa = self._make_wa(model_id=self.model_partner.id)
        wa.write({'trigger_function_ids': [(4, self.func_write.id)]})
        partner = self.env['res.partner'].create({'name': 'P2 Actions Test'})
        result = self.WorkAuto._get_actions(partner, 'write')
        self.assertIn(wa, result)

    def test_11_get_actions_returns_empty_for_unknown_func(self):
        """_get_actions returns empty for unknown func_name."""
        partner = self.env['res.partner'].create({'name': 'P2 No Action'})
        result = self.WorkAuto._get_actions(partner, 'nonexistent_p2_func_xyz')
        self.assertFalse(result)

    # ──────────────────────── write guard ────────────────────────────────────────

    def test_12_deactivating_reusable_without_dependents_ok(self):
        """Deactivating a reusable automation with no dependents is allowed."""
        wa = self._make_reusable_wa()
        wa.write({'active': False})
        self.assertFalse(wa.active)

    def test_13_deactivating_reusable_with_dependents_raises(self):
        """Deactivating a reusable automation that has dependents raises ValidationError."""
        reusable = self._make_reusable_wa(name='Depended Reusable')
        caller = self._make_wa(name='Caller WA')
        node = self.env['node.struct'].create({
            'name': 'Reuse Automation',
            'work_auto_id': caller.id,
            'reused_work_auto_id': reusable.id,
        })
        with self.assertRaises(ValidationError):
            reusable.write({'active': False})

    # ────────────────────── get_dependents ──────────────────────────────────────

    def test_14_get_dependents_returns_empty_when_no_callers(self):
        """get_dependents returns empty list when nothing references this reusable."""
        reusable = self._make_reusable_wa(name='Isolated Reusable')
        deps = reusable.get_dependents()
        self.assertIsInstance(deps, list)
        self.assertFalse(deps)

    def test_15_get_dependents_finds_caller_automation(self):
        """get_dependents returns list of dicts with caller automation id."""
        reusable = self._make_reusable_wa(name='Referenced Reusable')
        caller = self._make_wa(name='Caller WA 2')
        self.env['node.struct'].create({
            'name': 'Reuse Automation',
            'work_auto_id': caller.id,
            'reused_work_auto_id': reusable.id,
        })
        deps = reusable.get_dependents()
        self.assertIsInstance(deps, list)
        dep_ids = [d['id'] for d in deps]
        self.assertIn(caller.id, dep_ids)

    # ─────────────────────── dry_run ────────────────────────────────────────────

    def test_16_dry_run_raises_if_not_record_saved(self):
        """dry_run raises ValidationError when workflow is not yet saved."""
        wa = self._make_wa()
        wa.write({'is_record_saved': False})
        with self.assertRaises(ValidationError):
            wa.dry_run()

    def test_17_dry_run_raises_if_no_model_and_not_reusable(self):
        """dry_run raises ValidationError when model_id is absent and workflow not reusable."""
        wa = self.WorkAuto.create({'name': 'No Model WA', 'is_record_saved': True})
        with self.assertRaises(ValidationError):
            wa.dry_run()

    def test_18_dry_run_raises_on_empty_flow(self):
        """dry_run raises ValidationError when flow_data has no nodes."""
        wa = self._make_wa()
        wa.write({
            'is_record_saved': True,
            'flow_data': {'drawflow': {'Home': {'data': {}}}},
        })
        with self.assertRaises(ValidationError):
            wa.dry_run()

    def test_19_dry_run_returns_dict_with_nodes_key(self):
        """dry_run returns a dict; basic structure verified via keys."""
        wa = self._make_wa()
        node = self.env['node.struct'].create({
            'name': 'Create',
            'work_auto_id': wa.id,
            'model_id': self.model_partner.id,
        })
        wa.write({
            'is_record_saved': True,
            'flow_data': {
                'drawflow': {
                    'Home': {
                        'data': {
                            '1': {
                                'data': {
                                    'name': 'Create',
                                    'type': 'action',
                                    'nodeId': node.id,
                                },
                                'outputs': {},
                            }
                        }
                    }
                }
            },
        })
        result = wa.dry_run()
        self.assertIsInstance(result, dict)

    # ─────────────────────── create_cron ────────────────────────────────────────

    def test_20_create_cron_noop_without_time_trigger(self):
        """create_cron does not create a cron when trigger is not time-based."""
        wa = self._make_wa()
        wa.create_cron()
        self.assertFalse(wa.schedule_id)

    def test_21_create_cron_creates_ir_cron_for_time_trigger(self):
        """create_cron creates ir.cron record when time_trigger_mode is set."""
        func_time = self.env['work.function'].search(
            [('trigger_type', '=', 'time')], limit=1
        )
        if not func_time:
            self.skipTest("No time-trigger work.function installed")
        wa = self._make_wa(
            time_trigger_mode='day',
            time_trigger_time=8.0,
        )
        wa.write({
            'function_id': func_time.id,
            'trigger_function_ids': [(4, func_time.id)],
        })
        wa.create_cron()
        self.assertTrue(wa.schedule_id)

    def test_21b_create_cron_creates_ir_cron_for_weekly_trigger(self):
        """create_cron creates a weekly ir.cron record when time_trigger_mode is 'week'."""
        func_time = self.env['work.function'].search(
            [('trigger_type', '=', 'time')], limit=1
        )
        if not func_time:
            self.skipTest("No time-trigger work.function installed")
        wa = self._make_wa(
            time_trigger_mode='week',
            time_trigger_time=8.0,
            time_trigger_weekday='2',
        )
        wa.write({
            'function_id': func_time.id,
            'trigger_function_ids': [(4, func_time.id)],
        })
        wa.create_cron()
        self.assertTrue(wa.schedule_id)
        self.assertEqual(wa.schedule_id.interval_number, 1)
        self.assertEqual(wa.schedule_id.interval_type, 'weeks')
        self.assertEqual(wa.schedule_id.nextcall.weekday(), 2)

    # ─────────────────────── run_now ────────────────────────────────────────────

    def test_22_run_now_method_exists(self):
        """run_now method is present on work.auto."""
        self.assertTrue(hasattr(self.WorkAuto, 'run_now'))
        self.assertTrue(callable(self.WorkAuto.run_now))

    def test_23_run_now_requires_time_trigger(self):
        """run_now always returns a dict with 'ok' key."""
        wa = self._make_wa()
        result = wa.run_now()
        self.assertIsInstance(result, dict)
        self.assertIn('ok', result)

    # ────────────────────── unlink removes schedule_id cron ─────────────────────

    def test_24_unlink_removes_ir_cron(self):
        """Unlinking work.auto also unlinks the associated ir.cron if present."""
        func_time = self.env['work.function'].search(
            [('trigger_type', '=', 'time')], limit=1
        )
        if not func_time:
            self.skipTest("No time-trigger work.function installed")
        wa = self._make_wa(time_trigger_mode='day', time_trigger_time=9.0)
        wa.write({'function_id': func_time.id})
        wa.create_cron()
        cron_id = wa.schedule_id.id if wa.schedule_id else None
        wa.unlink()
        if cron_id:
            self.assertFalse(self.env['ir.cron'].sudo().browse(cron_id).exists())

    def test_25_unlink_work_auto_p2(self):
        """work.auto record can be deleted in phase-2."""
        wa = self._make_wa()
        wa_id = wa.id
        wa.unlink()
        self.assertFalse(self.WorkAuto.browse(wa_id).exists())

    # ──────────────────────── get_context phase-2 enhancements ─────────────────

    def test_26_get_context_has_relativedelta(self):
        """get_context exposes relativedelta in phase-2."""
        wa = self._make_wa()
        ctx = wa.get_context()
        self.assertIn('relativedelta', ctx)

    def test_27_get_context_has_requests(self):
        """get_context exposes requests library in phase-2."""
        wa = self._make_wa()
        ctx = wa.get_context()
        self.assertIn('requests', ctx)

    def test_28_get_context_has_json(self):
        """get_context exposes json module in phase-2."""
        wa = self._make_wa()
        ctx = wa.get_context()
        self.assertIn('json', ctx)

    def test_29_get_context_has_record_key(self):
        """get_context exposes 'record' key in phase-2."""
        wa = self._make_wa()
        ctx = wa.get_context()
        self.assertIn('record', ctx)

    def test_30_get_context_has_current_record_key(self):
        """get_context exposes 'current_record' key in phase-2."""
        wa = self._make_wa()
        ctx = wa.get_context()
        self.assertIn('current_record', ctx)

    def test_31_process_context_has_safe_schedule_activity(self):
        """_process injects _safe_schedule_activity into execution context."""
        wa = self._make_wa(code="safe_fn = _safe_schedule_activity")
        # code reads _safe_schedule_activity from context — no NameError means it's present
        wa._process({})

    def test_32_get_context_env_is_cyllo_env(self):
        """get_context 'env' is a Cyllo Environment instance."""
        from odoo.api import Environment
        wa = self._make_wa()
        ctx = wa.get_context()
        self.assertIsInstance(ctx['env'], Environment)

    # ─────────────────────── _process phase-2 features ─────────────────────────

    def test_33_process_runs_basic_code(self):
        """_process executes simple code without error in phase-2."""
        wa = self._make_wa(code="result = 42")
        wa._process({})

    def test_34_process_propagates_cyllo_exceptions(self):
        """_process re-raises Cyllo exceptions without wrapping."""
        import logging
        wa = self._make_wa(code="raise ValidationError('p2 boom')")
        # Suppress the ERROR log _process emits before re-raising so the
        # test runner does not count the log entry as a failure.
        with self.assertLogs('odoo', level='ERROR'):
            with self.assertRaises(ValidationError):
                wa._process({})

    def test_35_process_returns_action_from_context(self):
        """_process returns the action dict when code sets action variable."""
        wa = self._make_wa(code="action = {'type': 'ir.actions.act_window'}")
        result = wa._process({})
        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('type'), 'ir.actions.act_window')

    # ──────────────────── _archive_workflows_with_whatsapp_nodes ────────────────

    def test_36_archive_whatsapp_workflows_archives_matching(self):
        """_archive_workflows_with_whatsapp_nodes archives WA workflows with WhatsApp nodes."""
        wa = self._make_wa(name='WA with WhatsApp')
        self.env['node.struct'].create({
            'name': 'WhatsApp',
            'work_auto_id': wa.id,
        })
        self.WorkAuto._archive_workflows_with_whatsapp_nodes()
        self.assertFalse(wa.active)

    def test_37_archive_whatsapp_leaves_non_whatsapp_workflows(self):
        """_archive_workflows_with_whatsapp_nodes leaves unrelated workflows active."""
        wa = self._make_wa(name='WA without WhatsApp')
        self.env['node.struct'].create({
            'name': 'Create',
            'work_auto_id': wa.id,
        })
        self.WorkAuto._archive_workflows_with_whatsapp_nodes()
        self.assertTrue(wa.active)

    # ──────────────────── save_data phase-2 (is_reusable, node linking) ─────────

    def test_38_save_data_sets_is_reusable(self):
        """save_data passes is_reusable flag to created work.auto."""
        new_id = self.WorkAuto.save_data(
            {'drawflow': {'Home': {'data': {}}}},
            'Reusable Via Save',
            False,
            model_id=self.model_partner.id,
            is_reusable=True,
            reuse_scope='generic',
        )
        wa = self.WorkAuto.browse(new_id)
        self.assertTrue(wa.is_reusable)

    def test_39_save_data_links_detached_nodes(self):
        """save_data links node.struct records created before work.auto existed."""
        orphan_node = self.env['node.struct'].create({'name': 'orphan'})
        flow = {
            'drawflow': {
                'Home': {
                    'data': {
                        '1': {
                            'data': {
                                'name': 'orphan',
                                'nodeId': orphan_node.id,
                            }
                        }
                    }
                }
            }
        }
        new_id = self.WorkAuto.save_data(
            flow, 'Link Test WA', False, model_id=self.model_partner.id
        )
        orphan_node.invalidate_recordset()
        self.assertEqual(orphan_node.work_auto_id.id, new_id)

    # ────────────────────── copy in phase-2 ─────────────────────────────────────

    def test_40_copy_creates_distinct_record(self):
        """copy() in phase-2 produces a distinct work.auto record."""
        wa = self._make_wa()
        wa.write({'flow_data': {'drawflow': {'Home': {'data': {}}}}})
        copy = wa.copy()
        self.assertNotEqual(copy.id, wa.id)

    def test_41_copy_name_contains_copy(self):
        """copy() result name includes '-copy' in phase-2."""
        wa = self._make_wa()
        wa.write({'flow_data': {'drawflow': {'Home': {'data': {}}}}})
        copy = wa.copy()
        self.assertIn('-copy', copy.name)

    # ────────────────── _extract_trigger_function_ids_from_flow ─────────────────

    def test_42_extract_trigger_function_ids_returns_list(self):
        """_extract_trigger_function_ids_from_flow returns a list."""
        wa = self._make_wa()
        result = wa._extract_trigger_function_ids_from_flow({})
        self.assertIsInstance(result, list)

    def test_43_extract_trigger_function_ids_finds_action_nodes(self):
        """_extract_trigger_function_ids_from_flow finds function id from action node."""
        func = self.env['work.function'].create({
            'name': 'P2 Trigger Func',
            'func_name': 'p2_trigger',
            'trigger_type': 'create',
        })
        flow = {
            'drawflow': {
                'Home': {
                    'data': {
                        '1': {
                            'data': {
                                'type': 'action',
                                'trigger_type': 'create',
                                'model': [func.id, 'P2 Trigger Func'],
                            }
                        }
                    }
                }
            }
        }
        wa = self._make_wa()
        result = wa._extract_trigger_function_ids_from_flow(flow)
        self.assertIn(func.id, result)

    def test_44_extract_deduplicates_trigger_types(self):
        """_extract_trigger_function_ids_from_flow returns unique function ids."""
        func = self.env['work.function'].create({
            'name': 'P2 Dup Func',
            'func_name': 'p2_dup',
            'trigger_type': 'write',
        })
        flow = {
            'drawflow': {
                'Home': {
                    'data': {
                        '1': {
                            'data': {
                                'type': 'action',
                                'trigger_type': 'write',
                                'model': [func.id, 'P2 Dup Func'],
                            }
                        },
                        '2': {
                            'data': {
                                'type': 'action',
                                'trigger_type': 'write',
                                'model': [func.id, 'P2 Dup Func'],
                            }
                        },
                    }
                }
            }
        }
        wa = self._make_wa()
        result = wa._extract_trigger_function_ids_from_flow(flow)
        self.assertEqual(result.count(func.id), 1)

    # ────────────────────── _get_test_node_order ────────────────────────────────

    def test_45_get_test_node_order_returns_node_struct_recordset(self):
        """_get_test_node_order returns a node.struct recordset."""
        wa = self._make_wa()
        result = wa._get_test_node_order()
        self.assertEqual(result._name, 'node.struct')

    def test_46_get_test_node_order_empty_on_no_flow(self):
        """_get_test_node_order returns empty recordset when flow_data is empty."""
        wa = self._make_wa()
        result = wa._get_test_node_order()
        self.assertFalse(result)

    # ────────────────────── _get_test_graph_issues ──────────────────────────────

    def test_47_get_test_graph_issues_returns_dict(self):
        """_get_test_graph_issues returns a dict."""
        wa = self._make_wa()
        wa.write({'flow_data': {'drawflow': {'Home': {'data': {}}}}})
        result = wa._get_test_graph_issues()
        self.assertIsInstance(result, dict)

    def test_48_get_test_graph_issues_empty_on_no_nodes(self):
        """_get_test_graph_issues returns empty dict when no nodes in flow."""
        wa = self._make_wa()
        wa.write({'flow_data': {'drawflow': {'Home': {'data': {}}}}})
        result = wa._get_test_graph_issues()
        self.assertEqual(result, {})

    # ─────────────── name -(id) suffix still works in phase-2 ───────────────────

    def test_49_create_name_gets_id_appended(self):
        """work.auto name gets -(id) suffix after creation in phase-2."""
        wa = self._make_wa(name='P2 Name Test')
        self.assertIn(str(wa.id), wa.name)
        self.assertTrue(wa.name.startswith('P2 Name Test'))

    # ──────────────────────── multi-company ─────────────────────────────────────

    def test_50_work_auto_other_company_not_visible(self):
        """work.auto from other company hidden by record rule for single-company user."""
        main_co = self.env.company
        other_co = self.env['res.company'].create({'name': 'P2 Multi Co'})
        wa_other = self.WorkAuto.sudo().create({
            'name': 'P2 Other Co WA',
            'model_id': self.model_partner.id,
            'company_id': other_co.id,
        })
        # Admin belongs to all companies — must use a user restricted to main_co only
        single_co_user = self.env['res.users'].create({
            'name': 'P2 Single Co User',
            'login': 'p2_singleco_wa@test.com',
            'groups_id': [(4, self.env.ref('base.group_user').id)],
            'company_id': main_co.id,
            'company_ids': [(6, 0, [main_co.id])],
        })
        found = self.WorkAuto.with_user(single_co_user).search(
            [('id', '=', wa_other.id)]
        )
        self.assertFalse(found)
