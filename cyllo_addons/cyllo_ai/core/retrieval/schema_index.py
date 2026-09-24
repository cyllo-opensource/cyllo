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
"""
Cached, deterministic schema access (pull-don't-push).

In-memory, per-process, per-database cache over ``ir.model`` / ``ir.model.fields``
— the source of truth stays in the DB; this is just a fast reshaping of it.
Lazy-built on first use (build cost ~hundreds of ms), invalidated on registry
reload via ``chatbot.tools._register_hook``. Deliberately NOT persisted to
disk/DB: the metadata is re-derivable in one query, so persistence would only
add a staleness problem.

What it precomputes per field (the planner operates over this):
- type / relation target  → the relational graph as adjacency, used for
  dotted-path validation (``partner_id.country_id.code``) and join hints
- groupable / aggregatable → feeds read_group planning and validation
- business flag            → filters ERP machinery (message_*, activity_*,
  binary, …) out of prompts without losing it for execution

Validation helpers return corrective, "did you mean"-style errors so the agent
self-corrects in one loop step instead of failing silently.
"""
import difflib
import re
import threading

# read_group-compatible groupby types
GROUPABLE_TYPES = {'many2one', 'char', 'selection', 'boolean', 'date', 'datetime', 'integer'}
# numeric types that can be aggregated (sum/avg/min/max)
AGGREGATABLE_TYPES = {'integer', 'float', 'monetary'}
RELATIONAL_TYPES = {'many2one', 'one2many', 'many2many'}

# ERP machinery excluded from "business" views (prompt injection / describe);
# still present in the raw metadata so execution paths can use everything.
NON_BUSINESS_PREFIXES = ('message_', 'activity_', 'website_message_', 'access_', 'has_message')
NON_BUSINESS_FIELDS = {'create_uid', 'write_uid', 'write_date'}
NON_BUSINESS_TYPES = {'binary', 'html'}


class SchemaIndex:
    """Process-wide cached view of the Cyllo data model, per database."""

    # dbname -> {table2model, model2table, models_meta, auto_names, fields_meta}
    _cache = {}
    # guards cache build/mutation across worker threads (gevent monkey-patches
    # threading, so this is gevent-safe too)
    _lock = threading.RLock()

    def __init__(self, env):
        self.env = env

    # -- cache lifecycle -----------------------------------------------------

    def _data(self):
        db = self.env.cr.dbname
        data = SchemaIndex._cache.get(db)
        if data is None:
            with SchemaIndex._lock:
                data = SchemaIndex._cache.get(db)  # re-check inside the lock
                if data is None:
                    data = self._build()
                    SchemaIndex._cache[db] = data
        return data

    def _build(self):
        records = self.env['ir.model'].sudo().search([])
        registry = self.env.registry
        table2model, model2table, models_meta, auto_names = {}, {}, [], []
        searchable = set()
        for r in records:
            if r.table_name:
                table2model[r.table_name] = r.model
                model2table[r.model] = r.table_name
                # data models only: abstract engines (no table) are already
                # excluded; transient wizards hold UI state, never business data
                if not r.transient:
                    searchable.add(r.model)
            models_meta.append((r.model, r.name or ''))
            if not r.transient:
                cls = registry.get(r.model)
                if cls is not None and getattr(cls, '_auto', True):
                    auto_names.append(r.model)
        return {
            'table2model': table2model,
            'model2table': model2table,
            'models_meta': models_meta,     # [(model, human_name)]
            'auto_names': auto_names,
            'searchable': searchable,       # table-backed, non-transient
            'fields_meta': {},              # model -> {fname: meta dict}
            'columns': None,                # {table: frozenset(cols)} — lazy
        }

    @classmethod
    def invalidate(cls, dbname=None):
        """Drop the cache (called on module upgrade / registry reload)."""
        with cls._lock:
            if dbname:
                cls._cache.pop(dbname, None)
            else:
                cls._cache.clear()

    # -- name resolution (cached dict lookups) -------------------------------

    def model_from_table(self, table):
        return self._data()['table2model'].get(table, table)

    def table_from_model(self, model):
        return self._data()['model2table'].get(model, model)

    def auto_model_names(self):
        return list(self._data()['auto_names'])

    def has_model(self, model):
        """True if the model exists (has a table) in this database."""
        return model in self._data()['model2table']

    def is_searchable(self, model):
        """True for table-backed, non-transient models (real business data)."""
        return model in self._data()['searchable']

    # -- physical columns (for SQL-fragment validation) ----------------------

    def columns_for(self, table):
        """Return the physical column names of ``table``, or ``None`` if the
        table does not exist.

        This is the ``get_columns`` resolver ``sql_guard.validate_plan``
        expects: it validates that a table exists (``None`` → the plan is
        rejected) and yields the real column set an ``alias.column`` reference
        is checked against. Backed by ``information_schema`` (the ground truth
        of what a generated SELECT may reference), built once and cached per
        database, invalidated with the rest of the index on registry reload.

        It reports column *existence* only — never access; ACL/ir.rules are
        enforced separately by the caller against the derived model set.
        """
        data = self._data()
        cols = data['columns']
        if cols is None:
            with SchemaIndex._lock:
                cols = data['columns']  # re-check inside the lock
                if cols is None:
                    cols = self._build_columns()
                    data['columns'] = cols
        return cols.get(table)

    def _build_columns(self):
        """One query for every public-schema table's columns → {table: frozenset}."""
        self.env.cr.execute("""
            SELECT table_name, column_name
              FROM information_schema.columns
             WHERE table_schema = 'public'
        """)
        built = {}
        for table, column in self.env.cr.fetchall():
            built.setdefault(table, set()).add(column)
        return {t: frozenset(c) for t, c in built.items()}

    # -- deterministic search ------------------------------------------------

    def search_models(self, query, limit=40):
        """Return ``[{model, name}]`` matching keywords in the query."""
        words = [w for w in re.findall(r'[a-zA-Z_]+', (query or '').lower()) if len(w) > 2]
        if not words:
            return []
        data = self._data()
        hits = []
        for model, name in data['models_meta']:
            if model not in data['searchable']:
                continue
            hay = (model + ' ' + (name or '')).lower()
            if any(w in hay for w in words):
                hits.append({'model': model, 'name': name})
                if len(hits) >= limit:
                    break
        return hits

    # -- field metadata (rich, cached per model) ------------------------------

    def _fields_meta(self, models):
        """Ensure rich metadata is cached for ``models``; return {model: {fname: meta}}."""
        if not models:
            return {}
        data = self._data()
        result, to_query = {}, []
        for m in models:
            meta = data['fields_meta'].get(m)
            if meta is not None:
                result[m] = meta
            else:
                to_query.append(m)

        if to_query:
            records = self.env['ir.model.fields'].sudo().search(
                [('model', 'in', list(to_query)), ('store', '=', True)])
            built = {m: {} for m in to_query}
            for f in records:
                built.setdefault(f.model, {})[f.name] = {
                    'type': f.ttype,
                    'relation': f.relation or None,
                    'label': f.field_description or f.name,
                    'groupable': f.ttype in GROUPABLE_TYPES,
                    'aggregatable': f.ttype in AGGREGATABLE_TYPES and f.name != 'id',
                    'business': (
                        f.ttype not in NON_BUSINESS_TYPES
                        and f.name not in NON_BUSINESS_FIELDS
                        and not f.name.startswith(NON_BUSINESS_PREFIXES)
                    ),
                }
            with SchemaIndex._lock:
                for m in to_query:
                    data['fields_meta'][m] = built.get(m, {})
            for m in to_query:
                result[m] = built.get(m, {})
        return result

    def model_fields(self, model):
        """``{field_name: meta}`` for one model (cached)."""
        return self._fields_meta([model]).get(model, {})

    def field_meta(self, model, field):
        """Meta dict for one field, or None."""
        return self.model_fields(model).get(field)

    def groupable_fields(self, model):
        return sorted(n for n, m in self.model_fields(model).items()
                      if m['groupable'] and m['business'])

    def aggregatable_fields(self, model):
        return sorted(n for n, m in self.model_fields(model).items() if m['aggregatable'])

    def relations(self, model):
        """Adjacency of the relational graph: ``{field: target_model}``."""
        return {n: m['relation'] for n, m in self.model_fields(model).items()
                if m['relation']}

    # -- legacy API (kept for the SQL tier / analytics) -----------------------

    def fields_for_models(self, models, crud=False):
        """Dict model -> [field labels]. Includes x2many fields when crud=True."""
        metas = self._fields_meta(list(models or []))
        out = {}
        for m in (models or []):
            labels = []
            for fname in sorted(metas.get(m, {})):
                meta = metas[m][fname]
                if meta['type'] in ('many2many', 'one2many'):
                    if crud:
                        labels.append(f"{fname} ({meta['type']} → {meta['relation']})")
                else:
                    labels.append(fname)
            out[m] = labels
        return out

    # -- validation (corrective errors, "did you mean") -----------------------

    def suggest_fields(self, model, wrong_field, n=3):
        """Closest valid field names for a typo/hallucination."""
        return difflib.get_close_matches(wrong_field, list(self.model_fields(model)), n=n, cutoff=0.5)

    def validate_field_path(self, model, path):
        """
        Validate a (possibly dotted) field path like ``partner_id.country_id.code``
        starting from ``model``. Returns ``(ok, error_message)``.
        """
        current = model
        parts = [p for p in (path or '').split('.') if p]
        if not parts:
            return False, "Empty field path."
        for i, part in enumerate(parts):
            fields = self.model_fields(current)
            if not fields:
                return False, f"Unknown model '{current}'."
            meta = fields.get(part)
            if meta is None:
                sugg = self.suggest_fields(current, part)
                hint = f" Did you mean: {', '.join(sugg)}?" if sugg else ""
                return False, f"Unknown field '{part}' on {current}.{hint}"
            if i < len(parts) - 1:
                if not meta['relation']:
                    return False, (f"Field '{part}' on {current} is type "
                                   f"'{meta['type']}' and cannot be traversed with '.'")
                current = meta['relation']
        return True, ""

    def validate_domain(self, model, domain):
        """Validate every field path in an Odoo domain. Returns a list of errors."""
        errors = []
        for item in (domain or []):
            if isinstance(item, str):           # '&' '|' '!' operators
                continue
            if isinstance(item, (list, tuple)) and len(item) == 3:
                ok, err = self.validate_field_path(model, item[0])
                if not ok:
                    errors.append(err)
            else:
                errors.append(f"Invalid domain item: {item!r} (expected [field, op, value]).")
        return errors

    def validate_fields(self, model, field_names):
        """Validate a list of plain or dotted field names. Returns a list of errors."""
        errors = []
        for fname in (field_names or []):
            ok, err = self.validate_field_path(model, fname)
            if not ok:
                errors.append(err)
        return errors

    # -- rendering for the planner --------------------------------------------

    def compact_fields(self, model, max_fields=60):
        """One-line, business-only field listing for prompt injection."""
        metas = self.model_fields(model)
        parts = []
        for fname in sorted(metas):
            meta = metas[fname]
            if not meta['business']:
                continue
            if meta['relation']:
                parts.append(f"{fname}:{meta['type']}({meta['relation']})")
            else:
                parts.append(f"{fname}:{meta['type']}")
        extra = len(parts) - max_fields
        if extra > 0:
            parts = parts[:max_fields] + [f"…+{extra} more (use get_model_fields)"]
        return ", ".join(parts)

    def describe_model(self, model):
        """Full structured description (the ``get_model_fields`` tool payload)."""
        if not self.has_model(model):
            # suggest only searchable (table-backed, non-transient) models —
            # never report engines or wizards the caller can't actually query
            names = sorted(self._data()['searchable'])
            sugg = difflib.get_close_matches(model, names, n=3, cutoff=0.5)
            hint = f" Did you mean: {', '.join(sugg)}?" if sugg else ""
            return {'error': f"Unknown model '{model}'.{hint}"}
        metas = self.model_fields(model)
        return {
            'model': model,
            'fields': [
                {'name': n, 'type': m['type'], 'relation': m['relation'], 'label': m['label']}
                for n, m in sorted(metas.items()) if m['business']
            ],
            'groupable': self.groupable_fields(model),
            'aggregatable': self.aggregatable_fields(model),
        }
