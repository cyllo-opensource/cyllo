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
SQL guard — allowlist validation of LLM-authored query fragments.

``analytic_record`` asks the model for a structured query *plan*, then splices
that plan's fragments (SELECT items, JOIN conditions, WHERE clause, GROUP BY,
ORDER BY) into a single SELECT. Those fragments are attacker-influenced (prompt
injection via the user's chat message), so before any of them is wrapped in
``SQL()`` they must be proven safe.

The strategy is **accept-known-good, never reject-known-bad**: each fragment is
tokenized and parsed against a tight grammar that only permits a known-safe
subset; anything outside it is refused. A blacklist ("block the word SELECT")
loses to casing/comments/unicode tricks — an allowlist that only accepts
``identifier <op> %s`` shapes cannot express a subquery in the first place.

This module is **pure** — no Odoo ``env``, no SQL execution. It decides whether
a plan is shaped safely and derives the set of tables it touches; the caller
resolves models to physical tables, supplies a column resolver, and enforces
ACL / ir.rules against the derived table set.

Entry points:
- :func:`validate_plan` — validate a whole query plan; returns the derived
  security table set and every referenced identifier.
- :func:`validate_where` / :func:`validate_select` / :func:`validate_group_by`
  / :func:`validate_order_by` — per-clause validators (also used directly in
  tests).
- :func:`check_ident` — the shared ``alias.column`` check every clause reuses.

Contract for :func:`validate_plan`: all table/alias references in the plan are
already normalized to underscored physical table names (the caller resolves
model→table first — the WHERE tokenizer treats ``a.b`` as exactly one
``alias.column``, so dotted model names must not reach it).
"""
import re
from collections import namedtuple

# Pure scalar functions permitted to wrap a column. They touch no data, so they
# cannot be a smuggling vector as long as their arguments are themselves
# validated (identifier / placeholder / nested allowed function only). EXTRACT
# is deliberately absent: date filtering uses range comparisons
# (``date_col >= %s AND date_col < %s``), which are simpler and index-friendly.
SCALAR_FUNCS = frozenset({'LOWER', 'UPPER', 'COALESCE', 'DATE_TRUNC'})
# Aggregates — valid in SELECT / ORDER BY, not in WHERE / GROUP BY.
AGG_FUNCS = frozenset({'SUM', 'COUNT', 'AVG', 'MIN', 'MAX'})

# Per-clause function allowlists.
WHERE_FUNCS = SCALAR_FUNCS
GROUP_FUNCS = SCALAR_FUNCS
SELECT_FUNCS = SCALAR_FUNCS | AGG_FUNCS
ORDER_FUNCS = SCALAR_FUNCS | AGG_FUNCS

# Join kinds the planner may emit (matched case-insensitively, exact set).
JOIN_TYPES = frozenset({'JOIN', 'LEFT JOIN'})

# Bare words with grammatical meaning. Anything else bare (a table name, SELECT,
# DROP, an unknown function) is rejected by classification / parsing.
_KEYWORDS = frozenset({
    'AND', 'OR', 'NOT', 'IN', 'BETWEEN', 'IS', 'NULL', 'LIKE', 'ILIKE',
    'ASC', 'DESC', 'DISTINCT',
})

# A plain, safe SQL identifier (table / column / alias / output label). Used for
# the raw name strings in the plan (join aliases/columns, main table) that get
# f-string-interpolated — they must be nothing but an identifier.
_NAME_RE = re.compile(r'^[a-z_][a-z0-9_]*$')
# Allowed content of a string literal (only inside function args, e.g.
# DATE_TRUNC('month', col)). A conservative charset — no quotes, backslash,
# semicolon, parens or ``%`` — so it can never break out of the literal.
_SAFE_STRING_RE = re.compile(r'[A-Za-z0-9 _:.,+\-]*')
# Trailing output label on a SELECT item: ``<expr> AS name``.
_AS_RE = re.compile(r'\s+AS\s+([A-Za-z_][A-Za-z0-9_]*)\s*$', re.IGNORECASE)

# One master scanner. Order matters: %s, string and number literals must be
# tried before the bare-word and single-char rules. Any character not covered
# here is an illegal token — that is what rejects ``;``, ``$``, ``::`` casts,
# and stray metacharacters.
_TOKEN_RE = re.compile(
    r"""
      (?P<WS>\s+)
    | (?P<PLACEHOLDER>%s)
    | (?P<STRING>'[^'\\]*')
    | (?P<NUMBER>\d+(?:\.\d+)?)
    | (?P<IDENT>[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*)
    | (?P<WORD>[A-Za-z_][A-Za-z0-9_]*)
    | (?P<OP><=|>=|<>|!=|=|<|>)
    | (?P<ARITH>[-+*/])
    | (?P<LPAREN>\()
    | (?P<RPAREN>\))
    | (?P<COMMA>,)
    """,
    re.VERBOSE,
)

# What validate_plan returns: the derived security table set (for ACL/ir.rules)
# and every (alias, column) the plan references (already normalized lowercase).
ValidatedPlan = namedtuple('ValidatedPlan', ['tables', 'idents'])


class SqlGuardError(ValueError):
    """Raised when an LLM-authored fragment is not provably safe."""


def check_ident(alias, column, allowed_aliases, columns_of):
    """Validate a single ``alias.column`` reference; return it normalized.

    The alias must be one of the tables declared by the query (main table +
    joins), and the column must be a real column of that table. Together these
    guarantee a fragment can only ever reference tables already in the query's
    security set — closing the subquery/exfiltration hole.

    Identifiers are lowercased before the lookup, mirroring Postgres's folding
    of unquoted identifiers (quoted identifiers cannot occur — ``"`` is not a
    legal token). Over the ASCII identifier charset this fold is exactly
    Python ``str.lower()``, and it can only ever resolve to the same column
    Postgres would, so it adds no access. The normalized ``(alias, column)``
    is returned so callers collect a consistent security set regardless of the
    casing the model emitted.

    :param allowed_aliases: set of (lowercase) alias strings declared by the query.
    :param columns_of: ``{alias: set(column_names)}`` (lowercase) for those aliases.
    """
    alias, column = alias.lower(), column.lower()
    if alias not in allowed_aliases:
        raise SqlGuardError(
            f"unknown table alias {alias!r} "
            f"(declared: {', '.join(sorted(allowed_aliases)) or 'none'})")
    cols = columns_of.get(alias)
    if cols is not None and column not in cols:
        raise SqlGuardError(f"unknown column {alias}.{column}")
    return alias, column


def _safe_name(value, what):
    """Return a lowercased plain identifier or raise.

    For the raw name strings the plan supplies for interpolation (join
    aliases/columns, main table). Anything with a dot, space, quote, paren or
    other punctuation is rejected — these positions must be bare identifiers.
    """
    if not isinstance(value, str) or not _NAME_RE.match(value.lower()):
        raise SqlGuardError(f"invalid {what}: {value!r}")
    return value.lower()


# -- tokenizer ---------------------------------------------------------------

# Typed token tuples: (kind, value). kinds: IDENT (value=(alias, column)),
# PLACEHOLDER, OP, KW (value=UPPER keyword), FUNC (value=UPPER name),
# LPAREN, RPAREN, COMMA. The tokenizer does NOT decide whether a function name
# is allowed — that is policy, enforced per-clause by the parser.
def _tokenize(clause):
    """Scan a clause into typed tokens, or raise on any illegal input."""
    raw = []
    pos, n = 0, len(clause)
    while pos < n:
        m = _TOKEN_RE.match(clause, pos)
        if not m:
            raise SqlGuardError(
                f"illegal character {clause[pos]!r} at position {pos}")
        pos = m.end()
        kind = m.lastgroup
        if kind == 'WS':
            continue
        raw.append((kind, m.group()))

    tokens = []
    for idx, (kind, val) in enumerate(raw):
        if kind == 'IDENT':
            alias, column = val.split('.', 1)
            tokens.append(('IDENT', (alias, column)))
        elif kind == 'WORD':
            upper = val.upper()
            nxt = raw[idx + 1][0] if idx + 1 < len(raw) else None
            # Keyword classification wins over the function rule: a keyword such
            # as NOT may legitimately precede '(' (e.g. ``NOT (a = %s)``).
            if upper in _KEYWORDS:
                tokens.append(('KW', upper))
            elif nxt == 'LPAREN':
                tokens.append(('FUNC', upper))
            else:
                # A bare word (not a keyword, not a function call): a table name
                # without a column, SELECT, or a reference to a SELECT output
                # alias. Emitted as NAME; the parser accepts it only where an
                # output-alias reference is legal (ORDER BY / GROUP BY) and
                # rejects it everywhere else.
                tokens.append(('NAME', val))
        elif kind == 'STRING':
            tokens.append(('STRING', val[1:-1]))  # inner content, quotes stripped
        else:
            tokens.append((kind, val))
    return tokens


# -- parser (recursive descent) ----------------------------------------------

class _Parser:
    """Shared parsing primitives over a token stream.

    Holds the declared aliases, their columns, and the function allowlist for
    the clause being parsed. Applies :func:`check_ident` to every identifier
    and collects the normalized ``(alias, column)`` pairs in ``idents``.
    Subclass/entry methods add the clause-specific grammar.
    """

    def __init__(self, tokens, allowed_aliases, columns_of, funcs,
                 output_aliases=()):
        self._toks = tokens
        self._i = 0
        self._allowed = allowed_aliases
        self._cols = columns_of
        self._funcs = funcs
        # SELECT output labels an ORDER BY / GROUP BY term may reference by name
        # (already validated safe identifiers); empty for WHERE / SELECT.
        self._output_aliases = {a.lower() for a in (output_aliases or ())}
        self.idents = []

    # -- cursor helpers --
    def _peek(self):
        return self._toks[self._i] if self._i < len(self._toks) else (None, None)

    def _at(self, kind, val=None):
        k, v = self._peek()
        return k == kind and (val is None or v == val)

    def _advance(self):
        tok = self._toks[self._i]
        self._i += 1
        return tok

    def _expect(self, kind, val=None):
        if not self._at(kind, val):
            k, v = self._peek()
            want = f"{kind} {val}" if val else kind
            got = f"{k} {v}" if k else "end of clause"
            raise SqlGuardError(f"expected {want}, got {got}")
        return self._advance()

    def _end(self):
        if self._i != len(self._toks):
            k, v = self._peek()
            raise SqlGuardError(f"unexpected trailing token {v!r}")

    # -- shared operand grammar --
    def _record_ident(self):
        alias, column = self._advance()[1]
        self.idents.append(
            check_ident(alias, column, self._allowed, self._cols))

    def _operand(self):
        """An arithmetic expression: factor ( (+|-|*|/) factor )*.

        Flat (no parentheses) — that keeps this unambiguous with the WHERE
        boolean-grouping parens, and covers the common cases (``qty * price``,
        ``SUM(a) / SUM(b)``) without a groupable sub-expression grammar.
        """
        self._factor()
        while self._at('ARITH'):
            self._advance()
            self._factor()

    def _factor(self):
        if self._at('IDENT'):
            self._record_ident()
        elif self._at('NUMBER') or self._at('PLACEHOLDER'):
            # Numeric literals and bound params are injection-safe constants.
            self._advance()
        elif self._at('STRING'):
            # A string constant (e.g. DATE_TRUNC('month', col)). Safe-charset
            # validated so it can never break out of the quotes; it is a
            # constant, never a comparison RHS (those are PLACEHOLDER-only).
            val = self._advance()[1]
            if not _SAFE_STRING_RE.fullmatch(val):
                raise SqlGuardError(f"unsafe string literal {val!r}")
        elif self._at('NAME') and self._peek()[1].lower() in self._output_aliases:
            # A reference to a SELECT output alias (a validated label) — legal in
            # ORDER BY / GROUP BY. No table.column to add to the security set.
            self._advance()
        elif self._at('FUNC'):
            name = self._advance()[1]
            if name not in self._funcs:
                raise SqlGuardError(f"function {name!r} is not allowed here")
            self._expect('LPAREN')
            self._funcargs()
            self._expect('RPAREN')
        else:
            k, v = self._peek()
            got = f"{k} {v}" if k else "end of clause"
            raise SqlGuardError(f"expected a column, value or function, got {got}")

    def _funcargs(self):
        # Optional leading DISTINCT (COUNT(DISTINCT col)); COUNT(*) as a bare *.
        if self._at('KW', 'DISTINCT'):
            self._advance()
        if self._at('ARITH', '*'):
            self._advance()
            return
        self._operand()
        while self._at('COMMA'):
            self._advance()
            self._operand()

    # -- entry points --
    def parse_where(self):
        self._or_expr()
        self._end()
        return self.idents

    def parse_operand(self):
        """A single operand (one SELECT item's expression)."""
        self._operand()
        self._end()
        return self.idents

    def parse_operand_list(self):
        """Comma-separated operands (GROUP BY). Commas inside a function's
        argument list are handled by ``_funcargs``, so we split at the parser
        level, never by string."""
        self._operand()
        while self._at('COMMA'):
            self._advance()
            self._operand()
        self._end()
        return self.idents

    def parse_order_list(self):
        """Comma-separated operands each with an optional ASC/DESC."""
        self._order_term()
        while self._at('COMMA'):
            self._advance()
            self._order_term()
        self._end()
        return self.idents

    def _order_term(self):
        self._operand()
        if self._at('KW', 'ASC') or self._at('KW', 'DESC'):
            self._advance()

    # -- WHERE-only boolean grammar --
    def _or_expr(self):
        self._and_expr()
        while self._at('KW', 'OR'):
            self._advance()
            self._and_expr()

    def _and_expr(self):
        self._not_expr()
        while self._at('KW', 'AND'):
            self._advance()
            self._not_expr()

    def _not_expr(self):
        if self._at('KW', 'NOT'):
            self._advance()
            self._not_expr()
        else:
            self._primary()

    def _primary(self):
        if self._at('LPAREN'):
            self._advance()
            self._or_expr()
            self._expect('RPAREN')
        else:
            self._condition()

    def _condition(self):
        self._operand()
        k, v = self._peek()
        if k == 'OP' or (k == 'KW' and v in ('LIKE', 'ILIKE')):
            self._advance()
            self._expect('PLACEHOLDER')
        elif k == 'KW' and v == 'NOT':                 # a.x NOT LIKE %s
            self._advance()
            if not self._at('KW', 'LIKE') and not self._at('KW', 'ILIKE'):
                raise SqlGuardError("expected LIKE/ILIKE after NOT")
            self._advance()
            self._expect('PLACEHOLDER')
        elif k == 'KW' and v == 'IN':                  # a.x IN %s
            self._advance()
            self._expect('PLACEHOLDER')
        elif k == 'KW' and v == 'BETWEEN':             # a.x BETWEEN %s AND %s
            self._advance()
            self._expect('PLACEHOLDER')
            self._expect('KW', 'AND')
            self._expect('PLACEHOLDER')
        elif k == 'KW' and v == 'IS':                  # a.x IS [NOT] NULL
            self._advance()
            if self._at('KW', 'NOT'):
                self._advance()
            self._expect('KW', 'NULL')
        else:
            got = f"{k} {v}" if k else "end of clause"
            raise SqlGuardError(f"expected a comparison operator, got {got}")


# -- per-clause validators ---------------------------------------------------

def validate_where(clause, allowed_aliases, columns_of):
    """Validate an LLM-authored WHERE clause; return referenced identifiers.

    An empty or blank clause is valid and returns ``[]``. Raises
    :class:`SqlGuardError` with a corrective reason on anything outside the
    accepted subset — the reason is fed back to the model for a structured
    retry.
    """
    if not clause or not clause.strip():
        return []
    tokens = _tokenize(clause)
    if not tokens:
        return []
    return _Parser(tokens, allowed_aliases, columns_of, WHERE_FUNCS).parse_where()


def validate_select(items, allowed_aliases, columns_of):
    """Validate the SELECT list (a list of item strings); return identifiers.

    Each item is ``alias.column``, ``FUNC(...)`` (scalar or aggregate), or
    ``COUNT(*)``, with an optional ``AS label``. An empty/missing list is
    allowed (the query builder falls back to the main table's id).
    """
    idents = []
    for item in (items or []):
        if not isinstance(item, str) or not item.strip():
            raise SqlGuardError(f"invalid select item: {item!r}")
        # Strip the optional AS-label FIRST, then validate the expression — so
        # COUNT(*) AS n, SUM(x) AS total etc. all reach the grammar cleanly.
        m = _AS_RE.search(item)
        if m:
            _safe_name(m.group(1), "select output name")
            expr = item[:m.start()]
        else:
            expr = item
        tokens = _tokenize(expr)
        idents += _Parser(tokens, allowed_aliases, columns_of,
                          SELECT_FUNCS).parse_operand()
    return idents


def validate_group_by(clause, allowed_aliases, columns_of, output_aliases=()):
    """Validate a GROUP BY clause (comma-separated operands).

    ``output_aliases`` are SELECT output labels a term may reference by name
    (standard SQL); other bare words are still rejected.
    """
    if not clause or not str(clause).strip():
        return []
    tokens = _tokenize(str(clause))
    if not tokens:
        return []
    return _Parser(tokens, allowed_aliases, columns_of, GROUP_FUNCS,
                   output_aliases).parse_operand_list()


def validate_order_by(clause, allowed_aliases, columns_of, output_aliases=()):
    """Validate an ORDER BY clause (operands, each with optional ASC/DESC).

    ``output_aliases`` are SELECT output labels a term may reference by name
    (e.g. ``ORDER BY total DESC`` for ``SUM(...) AS total``); other bare words
    are still rejected.
    """
    if not clause or not str(clause).strip():
        return []
    tokens = _tokenize(str(clause))
    if not tokens:
        return []
    return _Parser(tokens, allowed_aliases, columns_of, ORDER_FUNCS,
                   output_aliases).parse_order_list()


def _output_names(items):
    """Collect the referenceable output names of a SELECT list — the ``AS``
    labels plus the plain column name of each ``table.column`` item — so
    ORDER BY / GROUP BY may reference them (as SQL allows)."""
    names = set()
    for item in (items or []):
        if not isinstance(item, str):
            continue
        m = _AS_RE.search(item)
        if m:
            names.add(m.group(1).lower())
            continue
        plain = re.fullmatch(
            r'\s*[A-Za-z_][A-Za-z0-9_]*\.([A-Za-z_][A-Za-z0-9_]*)\s*', item)
        if plain:
            names.add(plain.group(1).lower())
    return names


# -- whole-plan validator ----------------------------------------------------

def validate_plan(plan, get_columns):
    """Validate a whole query plan and derive its security table set.

    :param plan: the (already model→table normalized) query plan dict, with
        ``main_table`` {name, alias}, ``joins`` [...], ``select``, ``where``,
        ``group_by``, ``order_by``. The plan's self-reported ``tables`` list is
        deliberately ignored — the table set is derived here, not trusted.
    :param get_columns: callable ``table_name -> set(column_names) | None``.
        Returning ``None`` means the table is unknown/not queryable and the
        plan is rejected — so this doubles as table validation and must run as
        the requesting user's schema view.
    :returns: :class:`ValidatedPlan` (``tables``: set for ACL/ir.rules,
        ``idents``: all referenced ``(alias, column)`` pairs).
    :raises SqlGuardError: on anything outside the accepted subset.
    """
    if not isinstance(plan, dict):
        raise SqlGuardError("query plan must be an object")

    main = plan.get('main_table')
    if not isinstance(main, dict):
        raise SqlGuardError("main_table is required")
    main_alias = _safe_name(main.get('alias') or main.get('name'),
                            "main_table alias")
    main_table = _safe_name(main.get('name') or main.get('alias'),
                            "main_table name")
    main_cols = get_columns(main_table)
    if main_cols is None:
        raise SqlGuardError(f"unknown table {main_table!r}")

    # alias -> physical table, and alias -> column set. Aliases are the keys the
    # clause identifiers reference; the values give the security table set.
    alias_to_table = {main_alias: main_table}
    columns_of = {main_alias: main_cols}

    for j in (plan.get('joins') or []):
        if not isinstance(j, dict):
            raise SqlGuardError("each join must be an object")
        if str(j.get('type') or '').upper().strip() not in JOIN_TYPES:
            raise SqlGuardError(f"unsupported join type {j.get('type')!r}")
        lhs_alias = _safe_name(j.get('lhs_alias'), "join lhs_alias")
        lhs_column = _safe_name(j.get('lhs_column'), "join lhs_column")
        rhs_alias = _safe_name(j.get('rhs_alias'), "join rhs_alias")
        rhs_column = _safe_name(j.get('rhs_column'), "join rhs_column")
        rhs_table = _safe_name(j.get('rhs_table'), "join rhs_table")
        rhs_cols = get_columns(rhs_table)
        if rhs_cols is None:
            raise SqlGuardError(f"unknown table {rhs_table!r}")
        # The left side must reference an already-declared alias (joins are
        # validated in order); only then is the right side's alias introduced.
        check_ident(lhs_alias, lhs_column, set(alias_to_table), columns_of)
        alias_to_table[rhs_alias] = rhs_table
        columns_of[rhs_alias] = rhs_cols
        check_ident(rhs_alias, rhs_column, set(alias_to_table), columns_of)

    allowed = set(alias_to_table)
    select_items = plan.get('select')
    idents = []
    idents += validate_select(select_items, allowed, columns_of)
    # SELECT labels/columns that ORDER BY / GROUP BY may reference by name.
    output_aliases = _output_names(select_items)

    where = plan.get('where')
    if isinstance(where, dict):
        where_clause = where.get('where_clause') or ''
    elif isinstance(where, str):
        where_clause = where
    else:
        where_clause = ''
    idents += validate_where(where_clause, allowed, columns_of)

    idents += validate_group_by(plan.get('group_by'), allowed, columns_of,
                                output_aliases)
    idents += validate_order_by(plan.get('order_by'), allowed, columns_of,
                                output_aliases)

    return ValidatedPlan(tables=set(alias_to_table.values()), idents=idents)
