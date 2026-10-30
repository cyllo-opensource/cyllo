# -*- coding: utf-8 -*-
#############################################################################
#
#    Cyllo Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cyllo(<https://www.cyllo.com>)
#
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
from odoo import http
from odoo.http import Controller, request, route
import json


class AddToShortcuts(Controller):
    """Controller for managing user shortcuts."""

    @route('/add_to_shortcuts', type='json', auth='user')
    def add_to_shortcuts(self, actionId, name, model, menu_id,
                         action_context=None, action_domain=None,
                         view_type=None, active_record_id=None):
        """
            Adds a specific action identified by 'actionId' from the user's shortcuts.
            menu_id is stored for activation/highlight even when it is not the
            exact menu of the action (e.g. drilled kanban views like Receipts).
        """

        isMenu = request.env['ir.ui.menu'].sudo().search_count([
            ('action', 'like', f'ir.actions.act_window,{actionId}')
        ])
        try:
            if isinstance(menu_id, str):
                menu_id = int(menu_id.strip())
            elif menu_id is None or (isinstance(menu_id, float) and menu_id != menu_id):
                menu_id = False
            else:
                menu_id = int(menu_id)
        except (TypeError, ValueError):
            menu_id = False
        model_record = request.env['ir.model'].sudo().search(
            [('model', '=', model)], limit=1)
        if not model_record and actionId:
            # Derive the model from the action itself when the client
            # could not provide one (e.g. no searchModel in context).
            action = request.env['ir.actions.act_window'].sudo().browse(actionId)
            if action.exists() and action.res_model:
                model = action.res_model
                model_record = request.env['ir.model'].sudo().search(
                    [('model', '=', model)], limit=1)
        if not model_record:
            return {'error': 'Model not found'}
        menu_record = request.env['ir.ui.menu'].sudo().browse(menu_id) if menu_id else request.env['ir.ui.menu'].sudo().browse([])
        if not menu_record.exists():
            # Fall back to the first menu bound to this action instead of
            # failing (client may send NaN/undefined menu_id).
            menu_record = request.env['ir.ui.menu'].sudo().search(
                [('action', '=', f'ir.actions.act_window,{actionId}')],
                limit=1)
        if not menu_record.exists():
            return {'error': 'Menu not found'}
        menu_id = menu_record.id
        path = menu_record.complete_name
        if isMenu > 0 and '/' in path:
            path = path.rsplit('/', 1)[0]
        if isinstance(action_context, dict):
            action_context = json.dumps(action_context, sort_keys=True)
        if isinstance(action_domain, list):
            action_domain = json.dumps(action_domain, sort_keys=True)
        # Derive active_record_id from context when not sent explicitly.
        if active_record_id is None:
            try:
                ctx = json.loads(action_context) if isinstance(
                    action_context, str) else (action_context or {})
                active_record_id = int(ctx.get('active_id') or 0)
            except Exception:
                active_record_id = 0
        try:
            active_record_id = int(active_record_id or 0)
        except (TypeError, ValueError):
            active_record_id = 0
        Shortcut = request.env['shortcut.menu'].sudo()
        model_fields = Shortcut._fields
        # Idempotent per user: same action + same record + same view = one shortcut.
        # Each attempt runs in a savepoint so a missing-column error
        # (module not yet upgraded) does not abort the whole transaction.
        # Only filter on fields that actually exist on the model.
        existing = False
        try:
            with request.env.cr.savepoint():
                domain = [
                    ('create_uid', '=', request.env.user.id),
                    ('window_action_id', '=', actionId),
                ]
                if 'active_record_id' in model_fields:
                    domain.append(('active_record_id', '=', active_record_id))
                if 'view_type' in model_fields:
                    domain.append(('view_type', '=', view_type))
                existing = Shortcut.search(domain, limit=1)
        except Exception:
            existing = False
        if not existing:
            try:
                with request.env.cr.savepoint():
                    fallback = Shortcut.search([
                        ('create_uid', '=', request.env.user.id),
                        ('window_action_id', '=', actionId),
                    ], limit=1)
                    # Only treat as duplicate pre-upgrade when new columns
                    # are unusable; otherwise keep distinct per record/view.
                    if fallback and not self._shortcut_new_columns_usable():
                        existing = fallback
            except Exception:
                pass
        if existing:
            return True
        vals = {
            'name': name,
            'menu_id': menu_id,
            'window_action_id': actionId,
            'res_model': model_record.id,
            'path': path,
        }
        # Only include new fields if the column exists (allows running
        # before -u cyllo_base). After upgrade they are always stored.
        # NOTE: check _fields (not just DB columns) so stale DB columns
        # from older module versions can't inject invalid fields.
        if 'sequence' in model_fields:
            try:
                vals['sequence'] = self._next_shortcut_sequence()
            except Exception:
                pass
        try:
            if 'action_context' in model_fields:
                vals['action_context'] = action_context
            if 'action_domain' in model_fields:
                vals['action_domain'] = action_domain
            if 'view_type' in model_fields:
                vals['view_type'] = view_type
            if 'active_record_id' in model_fields:
                vals['active_record_id'] = active_record_id
        except Exception:
            pass
        try:
            with request.env.cr.savepoint():
                request.env['shortcut.menu'].sudo().create(vals)
        except Exception as e:
            # Fallback: DB columns missing (module not upgraded yet) or
            # stale extra keys -> strip every optional key and retry bare.
            for key in ('action_context', 'action_domain', 'view_type',
                        'active_record_id', 'sequence'):
                vals.pop(key, None)
            try:
                with request.env.cr.savepoint():
                    request.env['shortcut.menu'].sudo().create(vals)
            except Exception as e2:
                return {'error': str(e2) or str(e)}

        return True

    def _shortcut_new_columns_usable(self):
        """Check DB columns exist, not just _fields (code may be newer than DB)."""
        try:
            request.env.cr.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'shortcut_menu'
                AND column_name IN ('action_context', 'active_record_id', 'view_type')
            """)
            cols = {r[0] for r in request.env.cr.fetchall()}
            return {'action_context', 'active_record_id', 'view_type'} <= cols
        except Exception:
            return False

    @route('/add_app_to_shortcuts', type='json', auth='user')
    def add_app_to_shortcuts(self, menu_id=False, before_id=False, after_id=False):
        """Add an app (ir.ui.menu) to the current user's Quick Access.

        Derives the action/model server-side so sidebar drag-and-drop only
        needs to send the menu id. Idempotent per user + menu.
        before_id / after_id (shortcut ids) optionally pin the insert
        position so a drop between two tiles lands exactly there.
        Returns the shortcut id on success, True if already present.
        """
        try:
            menu_id = int(menu_id)
        except (TypeError, ValueError):
            return {'error': 'Invalid menu_id'}
        menu = request.env['ir.ui.menu'].browse(menu_id)
        if not menu.exists():
            return {'error': 'Menu not found'}
        # Keep the dropped (app) menu for name/path/dedup; only the action
        # may come from a descendant, mirroring how Odoo opens an app.
        _resolved_menu, action = self._resolve_menu_action(menu)
        window_action_id = False
        client_action_id = False
        server_action_id = False
        res_model_id = False
        if action and action.exists():
            if action._name == 'ir.actions.act_window':
                window_action_id = action.id
                if action.res_model:
                    model_rec = request.env['ir.model'].sudo().search(
                        [('model', '=', action.res_model)], limit=1)
                    if model_rec:
                        res_model_id = model_rec.id
            elif action._name == 'ir.actions.client':
                client_action_id = action.id
            elif action._name == 'ir.actions.server':
                server_action_id = action.id
        if not (window_action_id or client_action_id or server_action_id):
            return {'error': 'Menu has no action'}
        Shortcut = request.env['shortcut.menu'].sudo()
        existing = Shortcut.search([
            ('create_uid', '=', request.env.user.id),
            ('menu_id', '=', menu.id),
        ], limit=1)
        if existing:
            return {'id': existing.id, 'exists': True}
        vals = {
            'name': menu.name,
            'menu_id': menu.id,
            'path': menu.complete_name or menu.name,
        }
        if 'sequence' in request.env['shortcut.menu'].sudo()._fields:
            vals['sequence'] = self._next_shortcut_sequence()
        if window_action_id:
            vals['window_action_id'] = window_action_id
        if client_action_id:
            vals['client_action_id'] = client_action_id
        if server_action_id:
            vals['server_action_id'] = server_action_id
        if res_model_id:
            vals['res_model'] = res_model_id
        try:
            with request.env.cr.savepoint():
                rec = Shortcut.create(vals)
        except Exception as e:
            return {'error': str(e)}
        if 'sequence' in request.env['shortcut.menu'].sudo()._fields:
            try:
                self._place_shortcut_at(rec, before_id, after_id)
            except Exception:
                pass
        return {'id': rec.id}

    def _place_shortcut_at(self, rec, before_id=False, after_id=False):
        """Insert a new shortcut before/after an anchor sibling by
        renumbering the user's sequences (same idx*10 scheme as reorder).
        Unknown or foreign anchors fall back to the end."""
        anchor = False
        after = False
        try:
            if before_id:
                anchor = int(before_id)
            elif after_id:
                anchor = int(after_id)
                after = True
        except (TypeError, ValueError):
            anchor = False
        Shortcut = request.env['shortcut.menu'].sudo()
        recs = Shortcut.search(
            [('create_uid', '=', request.env.user.id)],
            order='sequence, id')
        ids = [r.id for r in recs if r.id != rec.id]
        if anchor and anchor in ids:
            idx = ids.index(anchor) + (1 if after else 0)
            ids.insert(idx, rec.id)
        else:
            ids.append(rec.id)
        for index, sid in enumerate(ids):
            Shortcut.browse(sid).write({'sequence': (index + 1) * 10})

    def _resolve_menu_action(self, menu):
        """Return (menu, action), descending to the first child with an
        action when the menu itself (e.g. a top-level app) has none —
        mirroring how Odoo opens an app on click."""
        seen = set()
        current = menu
        Menu = request.env['ir.ui.menu']
        while current and current.exists() and current.id not in seen:
            seen.add(current.id)
            action = current.action
            if action and action.exists():
                return current, action
            current = Menu.search(
                [('parent_id', '=', current.id)],
                order='sequence, id', limit=1)
        return menu, request.env['ir.actions.actions'].browse([])

    def _shortcut_table_ready(self):
        """New shortcut/folder columns exist in DB (module upgraded)."""
        try:
            request.env.cr.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'shortcut_menu'
                AND column_name IN ('sequence', 'folder_id')
            """)
            cols = {r[0] for r in request.env.cr.fetchall()}
            if {'sequence', 'folder_id'} - cols:
                return False
            request.env.cr.execute("""
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'shortcut_folder'
            """)
            return bool(request.env.cr.fetchone())
        except Exception:
            return False

    def _next_shortcut_sequence(self):
        try:
            Shortcut = request.env['shortcut.menu'].sudo()
            last = Shortcut.search(
                [('create_uid', '=', request.env.user.id)],
                order='sequence desc', limit=1)
            return (last.sequence or 0) + 10
        except Exception:
            return 10

    def _own_shortcuts(self, ids):
        try:
            ids = [int(i) for i in ids]
        except (TypeError, ValueError):
            return request.env['shortcut.menu'].sudo().browse([])
        return request.env['shortcut.menu'].sudo().search([
            ('id', 'in', ids),
            ('create_uid', '=', request.env.user.id),
        ])

    def _own_folder(self, folder_id):
        try:
            folder_id = int(folder_id)
        except (TypeError, ValueError):
            return request.env['shortcut.folder'].sudo().browse([])
        folder = request.env['shortcut.folder'].sudo().browse(folder_id)
        if not folder.exists() or folder.create_uid.id != request.env.user.id:
            return request.env['shortcut.folder'].sudo().browse([])
        return folder

    def _delete_empty_folders(self):
        """Ubuntu behaviour: a folder with no items deletes itself.
        Only touches the current user's folders."""
        try:
            if 'shortcut.folder' not in request.env:
                return
            Folder = request.env['shortcut.folder'].sudo()
            Shortcut = request.env['shortcut.menu'].sudo()
            folders = Folder.search(
                [('create_uid', '=', request.env.user.id)])
            for folder in folders:
                members = Shortcut.search_count([
                    ('folder_id', '=', folder.id),
                    ('create_uid', '=', request.env.user.id),
                ])
                if not members:
                    folder.unlink()
        except Exception:
            pass

    @route('/quick_access/reorder', type='json', auth='user')
    def quick_access_reorder(self, order=None):
        """Persist top-level order. order = [{type, id}] -> sequence = idx*10."""
        Shortcut = request.env['shortcut.menu'].sudo()
        if 'sequence' not in Shortcut._fields:
            return {'error': 'Please update the Cyllo Base module and try again.'}
        use_folder = ('folder_id' in Shortcut._fields
                      and 'shortcut.folder' in request.env)
        Folder = request.env['shortcut.folder'].sudo() if use_folder else False
        order = order or []
        uid = request.env.user.id
        for index, item in enumerate(order):
            seq = (index + 1) * 10
            try:
                if item.get('type') == 'folder' and use_folder:
                    folder = Folder.browse(int(item.get('id')))
                    if folder.exists() and folder.create_uid.id == uid:
                        folder.write({'sequence': seq})
                elif item.get('type') != 'folder':
                    rec = Shortcut.browse(int(item.get('id')))
                    if rec.exists() and rec.create_uid.id == uid:
                        vals = {'sequence': seq}
                        if use_folder:
                            vals['folder_id'] = False
                        rec.write(vals)
            except (TypeError, ValueError, AttributeError):
                continue
        self._delete_empty_folders()
        return True

    @route('/quick_access/create_folder', type='json', auth='user')
    def quick_access_create_folder(self, name=None, shortcut_ids=None, target_id=False):
        """Create a folder with the given shortcuts (min 1). Returns folder id.
        The folder takes the drop-target's on-screen slot (target_id): the
        target's visual index in the pre-merge top order, so dropping onto
        the first tile of a row keeps the folder in that row instead of
        slipping to the previous one. Without a target, the earliest member
        slot is used (multi-select path). Position is enforced by splicing
        plus renumbering, not just by copying the sequence value (which
        alone can still sort last on id tie-breaks)."""
        if not self._shortcut_table_ready():
            return {'error': 'Please update the Cyllo Base module and try again.'}
        recs = self._own_shortcuts(shortcut_ids or [])
        if not recs:
            return {'error': 'No shortcuts selected'}
        uid = request.env.user.id
        Shortcut = request.env['shortcut.menu'].sudo()
        Folder = request.env['shortcut.folder'].sudo()
        # Pre-merge top order to resolve the drop slot as an index.
        try:
            pre_shorts = Shortcut.search(
                [('create_uid', '=', uid), ('folder_id', '=', False)],
                order='sequence, id')
            pre_folders = Folder.search(
                [('create_uid', '=', uid)], order='sequence, id')
        except Exception:
            pre_shorts = recs.filtered(lambda r: not r.folder_id)
            pre_folders = Folder.browse([])
        pre = sorted(
            [('shortcut', r.id, r.sequence or 0) for r in pre_shorts]
            + [('folder', f.id, f.sequence or 0) for f in pre_folders],
            key=lambda x: (x[2], x[1]))
        member_ids = set(recs.ids)
        try:
            target_key = str(int(target_id)) if target_id else False
        except (TypeError, ValueError):
            target_key = False
        target_idx = None
        if target_key:
            for i, (kind, iid, _seq) in enumerate(pre):
                if kind == 'shortcut' and str(iid) == target_key:
                    target_idx = i
                    break
        if target_idx is None:
            # Fallback: earliest member slot.
            for i, (kind, iid, _seq) in enumerate(pre):
                if kind == 'shortcut' and iid in member_ids:
                    target_idx = i
                    break
        if target_idx is not None:
            # Visual slot: the target's on-screen index in the pre-merge
            # order. The dragged tile's old cell collapses (no gap is
            # reserved for it), so do NOT subtract members before the
            # target — subtracting is what pulled the folder one cell
            # early, into the previous row when the target led its row.
            insert_at = target_idx
        else:
            insert_at = None
        folder_seq = False
        try:
            if target_id:
                target = self._own_shortcuts([target_id])
                if target:
                    folder_seq = target.sequence or 10
        except (TypeError, ValueError):
            folder_seq = False
        if not folder_seq:
            recs_sorted = recs.sorted(key=lambda r: (r.sequence or 0, r.id))
            folder_seq = recs_sorted[0].sequence or 10
        folder = request.env['shortcut.folder'].sudo().create({
            'name': (name or 'New Folder').strip() or 'New Folder',
            'sequence': folder_seq,
        })
        recs.write({'folder_id': folder.id})
        # Enforce the drop slot: rebuild the top order with the new folder
        # spliced at the target index, then renumber idx*10.
        try:
            post_shorts = Shortcut.search(
                [('create_uid', '=', uid), ('folder_id', '=', False)],
                order='sequence, id')
            post_folders = Folder.search(
                [('create_uid', '=', uid), ('id', '!=', folder.id)],
                order='sequence, id')
            post = sorted(
                [('shortcut', r.id, r.sequence or 0) for r in post_shorts]
                + [('folder', f.id, f.sequence or 0) for f in post_folders],
                key=lambda x: (x[2], x[1]))
            if insert_at is None:
                insert_at = len(post)
            insert_at = max(0, min(insert_at, len(post)))
            final = post[:insert_at] + [('folder', folder.id, 0)] + post[insert_at:]
            for index, (kind, iid, _s) in enumerate(final):
                seq = (index + 1) * 10
                if kind == 'folder':
                    Folder.browse(iid).write({'sequence': seq})
                else:
                    Shortcut.browse(iid).write({'sequence': seq})
        except Exception:
            pass
        return {'id': folder.id}

    @route('/quick_access/move_to_folder', type='json', auth='user')
    def quick_access_move_to_folder(self, shortcut_ids=None, folder_id=False,
                                    before_id=False, after_id=False):
        """Move shortcuts into a folder (or back to top level when False).
        before_id/after_id optionally pin the top-level position (drop-out)."""
        if not self._shortcut_table_ready():
            return {'error': 'Please update the Cyllo Base module and try again.'}
        recs = self._own_shortcuts(shortcut_ids or [])
        if not recs:
            return {'error': 'No shortcuts selected'}
        if not folder_id:
            top = request.env['shortcut.menu'].sudo().search(
                [('create_uid', '=', request.env.user.id),
                 ('folder_id', '=', False)],
                order='sequence desc', limit=1)
            recs.write({
                'folder_id': False,
                'sequence': ((top.sequence or 0) + 10),
            })
            for rec in recs:
                try:
                    self._place_shortcut_at(rec, before_id, after_id)
                except Exception:
                    pass
            self._delete_empty_folders()
            return True
        folder = self._own_folder(folder_id)
        if not folder:
            return {'error': 'Folder not found'}
        recs.write({'folder_id': folder.id})
        self._delete_empty_folders()
        return True

    @route('/quick_access/rename_folder', type='json', auth='user')
    def quick_access_rename_folder(self, folder_id=False, name=None):
        if not self._shortcut_table_ready():
            return {'error': 'Please update the Cyllo Base module and try again.'}
        folder = self._own_folder(folder_id)
        if not folder:
            return {'error': 'Folder not found'}
        folder.write({'name': (name or '').strip() or folder.name})
        return True

    @route('/quick_access/delete_folder', type='json', auth='user')
    def quick_access_delete_folder(self, folder_id=False):
        """Delete a folder, keeping its shortcuts at top level (ungroup)."""
        if not self._shortcut_table_ready():
            return {'error': 'Please update the Cyllo Base module and try again.'}
        folder = self._own_folder(folder_id)
        if not folder:
            return {'error': 'Folder not found'}
        members = request.env['shortcut.menu'].sudo().search([
            ('folder_id', '=', folder.id),
            ('create_uid', '=', request.env.user.id),
        ])
        seq = folder.sequence or 10
        for rec in members.sorted(key=lambda r: (r.sequence or 0, r.id)):
            seq += 10
            rec.write({'folder_id': False, 'sequence': seq})
        folder.unlink()
        return True

    @route('/quick_access/remove_shortcut', type='json', auth='user')
    def quick_access_remove_shortcut(self, shortcut_id=False):
        recs = self._own_shortcuts([shortcut_id] if shortcut_id else [])
        if not recs:
            return {'error': 'Shortcut not found'}
        recs.unlink()
        self._delete_empty_folders()
        return True

    @route('/remove_from_shortcuts', type='json', auth='user')
    def remove_from_shortcuts(self, actionId, active_record_id=None,
                              view_type=None, name=None):
        """
            Removes the current user's shortcut matching the given action.
            Scoped by user + action + record + view so Receipts vs Delivery
            (same actionId, different active_id) and different users do not
            wipe each other.
        """
        domain = [
            ('create_uid', '=', request.env.user.id),
            ('window_action_id', '=', actionId),
        ]
        if active_record_id is not None:
            try:
                domain.append(
                    ('active_record_id', '=', int(active_record_id or 0)))
            except (TypeError, ValueError):
                pass
        if view_type:
            domain.append(('view_type', '=', view_type))
        if name:
            domain.append(('name', '=', name))
        try:
            with request.env.cr.savepoint():
                request.env['shortcut.menu'].sudo().search(domain).unlink()
        except Exception:
            # Pre-upgrade fallback: only user + action scoping.
            try:
                with request.env.cr.savepoint():
                    request.env['shortcut.menu'].sudo().search([
                        ('create_uid', '=', request.env.user.id),
                        ('window_action_id', '=', actionId),
                    ]).unlink()
            except Exception:
                pass
        return True

    @http.route('/get_idle_time/timer', auth='public', type='json')
    def get_idle_time(self):
        """
            Getting the idle time set inside res.user.
        """
        if request.env.user.idle_timer:
            return request.env.user.idle_time
