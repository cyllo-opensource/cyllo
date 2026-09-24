##################################
|TITLE| (|DATE|)
##################################

.. |TITLE| replace:: Cyllo Guidelines
.. |DATE| replace:: 2024/05/08

.. contents:: Table of contents
    :depth: 4

.. sectnum::



************
Introduction
************

This page introduces the coding guidelines for projects hosted under Cyllo. These
guidelines aim to improve the quality of the code: better readability of
source, better maintainability, better stability and fewer regressions.

Modules
=======

* Use 'cyllo_' as the prefix to your module name, for example if you are creating a module named 'base'
  then name the module as 'cyllo_base'.
* If your module's purpose is to serve as a base for other modules, prefix its
  name with `base_`. I.e. `base_location_nuts`.
* When creating a localization module, prefix its name with `l10n_CC_`, where
  `CC` is its country code. I.e. `l10n_es_pos`.
* In `__manifest__.py`:

  * Avoid empty keys
  * Make sure it has the `license` and `images` keys.
  * Make sure the text `,Cyllo` is appended to the
    `author` text.
  * The `website` key must be `https://www.cyllo.com`,
    so as to provide the most relevant link to discover more information about the addon.

Version numbers
===============

The version number in the module manifest should be the Cyllo major
version (e.g. `1.0`) followed by the module `x.y` version numbers.
For example: `1.0` is expected for the first release of an 1.0
module.

The `x.y.z` version numbers follow the semantics `breaking.feature.fix`:

* `x` increments when the data model or the views had significant
  changes. Data migration might be needed, or depending modules might be affected.
* `y` increments when non-breaking new features are added. A module
  upgrade will probably be needed.
* `z` increments when bugfixes were made. Usually a server restart
  is needed for the fixes to be made available.

If applicable, breaking changes are expected to include instructions
or scripts to perform migration on current installations.

Directories
===========

A module is organized in a few directories:

* `controllers/`: contains controllers (http routes)
* `data/`: data xml
* `demo/`: demo xml
* `examples/`: external files
  `lib/`, ...
* `models/`: model definitions
* `reports/`: reporting models (BI/analysis), Webkit/RML print report templates
* `static/`: contains the web assets, separated into `css/`, `js/`, `img/`,
* `templates/`: if you have several web templates and several backend views you can split them here
* `views/`: contains the views and templates, and QWeb report print templates
* `wizards/`: wizard model and views


File naming
===========

For `models`, `views` and `data` declarations, split files by the model
involved, either created or inherited. When they are XML files, a suffix should
be included with its category. For example, demo data for res.partner should go
in a file named `demo/res_partner_demo.xml` and a view for partner should go in
a file named `views/res_partner_views.xml`. An exception can be made when the
model is a model intended to be used only as a one2many model nested on the
main model. In this case, you can include the model definition inside it.
Example `sale.order.line` model can be together with `sale.order` in
the file `models/sale_order.py`.

For model named `<main_model>` the following files may be created:

* `models/<main_model>.py`
* `data/<main_model>_data.xml`
* `demo/<main_model>_demo.xml`
* `templates/<main_model>_template.xml`
* `views/<main_model>_views.xml`

For `controller`, if there is only one file it should be named `main.py`.
If there are several controller classes or functions you can split them into
several files.

For `static files`, the name pattern is `<module_name>.ext` (i.e.
`static/js/im_chat.js`, `static/css/im_chat.css`, `static/xml/im_chat.xml`,
...). Don't link data (image, libraries) outside Odoo: don't use an url to an
image but copy it in our codebase instead.

Installation hooks
==================

When **`pre_init_hook`**, **`post_init_hook`**, **`uninstall_hook`**
and **`post_load`** are
used, they should be placed in **`hooks.py`** located at the root of module
directory structure and keys in the manifest file keeps the same as the
following

.. code-block:: python

    {
        'pre_init_hook': 'pre_init_hook',
        'post_init_hook': 'post_init_hook',
        'uninstall_hook': 'uninstall_hook',
        'post_load': 'post_load',
    }

Remember to add into the **`__init__.py`** the following imports as
needed. For example:

.. code-block:: python

    from .hooks import pre_init_hook, post_init_hook, uninstall_hook, post_load

For applying monkey patches use post_load hook.
In order to apply them just if the module is installed.

Complete structure
==================

The complete tree should look like this:

.. code-block::

    addons/<my_module_name>/
    |-- __init__.py
    |-- __manifest__.py
    |-- hooks.py
    |-- controllers/
    |   |-- __init__.py
    |   `-- main.py
    |-- data/
    |   `-- <main_model>.xml
    |-- demo/
    |   `-- <inherited_model>.xml
    |-- migrations/
    |   `-- 12.0.x.y.z/
    |       |-- pre_migration.py
    |       `-- post_migration.py
    |-- models/
    |   |-- __init__.py
    |   |-- <main_model>.py
    |   `-- <inherited_model>.py
    |-- reports/
    |   |-- __init__.py
    |   |-- reports.xml
    |   |-- <bi_reporting_model>.py
    |   |-- report_<rml_report_name>.rml
    |   |-- report_<rml_report_name>.py
    |   |-- report_<qweb_report>.xml
    |   `-- <webkit_report_name>.mako
    |-- security/
    |   |-- ir.model.access.csv
    |   `-- <main_model>_security.xml
    |-- static/
    |   |-- img/
    |   |   |-- my_little_kitten.png
    |   |   `-- troll.jpg
    |   |-- lib/
    |   |   `-- external_lib/
    |   `-- src/
    |       |-- js/
    |       |   `-- <my_module_name>.js
    |       |-- css/
    |       |   `-- <my_module_name>.css
    |       |-- less/
    |       |   `-- <my_module_name>.less
    |       `-- xml/
    |           `-- <my_module_name>.xml
    |-- tests/
    |   |-- __init__.py
    |   |-- <test_file>.py
    |   `-- <test_file>.yml
    |-- views/
    |   |-- <main_model>_views.xml
    |   |-- <inherited_main_model>_views.xml
    |-- templates/
    |   |-- <main_model>.xml
    |   `-- <inherited_main_model>.xml
    |-- wizards/
    |   |-- __init__.py
    |   |-- <wizard_model>.py
    |   `-- <wizard_model>.xml
    `-- examples/
        `-- my_example.csv

Filenames should use only `[a-z0-9_]`

Use correct file permissions: folders 755 and files 644.

External dependencies
=====================

Manifest
--------

`__manifest__.py`

If your module uses extra dependencies of python or binaries you should add
the `external_dependencies` section to `__manifest__.py`.

.. code-block:: python

    {
        'name': 'Example Module',
        'external_dependencies': {
            'bin': [
                'external_dependency_binary_1',
                'external_dependency_binary_2',
            ],
            'python': [
                'external_dependency_python_1',
                'external_dependency_python_2',
            ],
        },
        'installable': True,
    }

An entry in `bin` needs to be in `PATH`, check by running
`which external_dependency_binary_N`.

An entry in `python` needs to be in `PYTHONPATH`, check by running
`python -c "import external_dependency_python_N"`.

README
------

If your module uses extra dependencies of python or binaries, please explain
how to install them in the `README.rst` file in the section `Installation`.

requirements.txt
----------------

As specified in `the Repositories Section <#repositories>`_, you should also define
the python packages to install in a file `requirements.txt` in the
root folder of the repository. This will be used for travis.


*********
XML files
*********

Format
======

When declaring a record in XML:

* Indent using four spaces
* Place `id` attribute before `model`
* For field declarations, the `name` attribute is first. Then place the `value`
  either in the `field` tag, either in the `eval` attribute, and finally other
  attributes (widget, options, ...) ordered by importance.
* Try to group the records by model. In case of dependencies between
  action/menu/views, the convention may not be applicable.
* Use naming convention defined at the next point
* The tag `<data>` is only used to set not-updatable data with `noupdate=1`
  when your data file contains a mix of "noupdate" data. Otherwise, you should
  use one of these:

  - `<odoo>`: for `noupdate=0` or demo data (demo data is non-updatable by default)
  - `<odoo noupdate='1'>`

* Do not prefix the xmlid by the current module's name
  (`<record id="view_id"...`, not `<record id="current_module.view_id"...`)

Naming xml_id
=============


Example For a new tree view(rental.order)
-----------------------------------------

.. code-block:: xml

    <record id="view_rental_order_tree" model="ir.ui.view">
        <field name="name">view.rental.order.tree</field>
        <field name="model">rental.order</field>
        <field name="priority" eval="16"/>
        <field name="arch" type="xml">
            <tree>
                <field name="my_field_1"/>
            </tree>
        </field>
    </record>

Example For a new form view(rental.order)
-----------------------------------------

.. code-block:: xml

    <record id="view_rental_order_form" model="ir.ui.view">
        <field name="name">view.rental.order.form</field>
        <field name="model">rental.order</field>
        <field name="priority" eval="16"/>
        <field name="arch" type="xml">
            <form>
                <sheet>
                    <group>
                        <field name="my_field_1"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

Example For a Window Action(ir.actions.act_window)(For the menu with label General Ledger)

.. code-block:: xml

    <record id="action_view_general_ledger" model="ir.actions.act_window">
        ...
    </record>

Example For a Server Action(ir.actions.server)(With function name action_quotation_sent)

.. code-block:: xml

    <record id="model_MODEL_NAME_FUNCTION_NAME" model="ir.actions.act_window">
        ...
    </record>

Example For a Report Action(ir.actions.report)(For Reports)

.. code-block:: xml

    <record id="report_REPORT_NAME_REPORT_TYPE" model="ir.actions.report">
        ...
    </record>

EXAMPLE

.. code-block:: xml

    <record id="report_invoice_pdf" model="ir.actions.report">
       <field name="name">Invoice</field>
       <field name="model">account.move</field>
       <field name="report_type">qweb-pdf</field>
    </record>

Example For a User Group(rental.order)
--------------------------------------

.. code-block:: xml

    <record id="group_rental_order_user" model="res.groups">
        ...
    </record>

    <record id="group_rental_order_admin" model="res.groups">
        ...
    </record>

Example For a Record Rule(rental.order)
---------------------------------------

.. code-block:: xml

    <record id="rule_rental_order_public" model="ir.rule">
        ...
    </record>

    <record id="rule_rental_order_company" model="ir.rule">
        ...
    </record>


Example For inheriting form view(rental.order)
----------------------------------------------

ORIGINAL VIEW

.. code-block:: xml

    <record id="view_order_form" model="ir.ui.view">
        <field name="name">sale.order.form</field>
        <field name="model">sale.order</field>
        <field name="priority" eval="16"/>
        <field name="arch" type="xml">
            <form>
                <sheet>
                    <group>
                        <field name="my_field_1"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

INHERITED VIEW

.. code-block:: xml

    <record id="view_sale_order_form" model="ir.ui.view">
        <field name="name">view.sale.order.form</field>
        <field name="model">sale.order</field>
        <field name="priority">110</field> <!--Priority greater than 100-->
        <field name="inherit_id" ref="sale.view_order_form"/>
        <field name="arch" type="xml">
            <!-- It is necessary because...-->
            <xpath expr="//field[@name='my_field_1']" position="replace"/>
        </field>
    </record>

Example For inheriting tree view(sale.order)
----------------------------------------------

ORIGINAL VIEW

.. code-block:: xml

    <record id="view_order_tree" model="ir.ui.view">
        <field name="name">sale.order.tree</field>
        <field name="model">sale.order</field>
        <field name="priority" eval="16"/>
        <field name="arch" type="xml">
            <tree>
                <field name="my_field_1"/>
            </tree>
        </field>
    </record>

INHERITED VIEW

.. code-block:: xml

    <record id="view_sale_order_tree" model="ir.ui.view">
        <field name="name">view.sale.order.form</field>
        <field name="model">sale.order</field>
        <field name="priority">110</field> <!--Priority greater than 100-->
        <field name="inherit_id" ref="sale.view_order_tree"/>
        <field name="arch" type="xml">
            <!-- It is necessary because...-->
            <xpath expr="//field[@name='my_field_1']" position="replace"/>
        </field>
    </record>
MENUITEM

ROOT MENU (With no parent and action)

.. code-block::xml

    <menuitem id="menu_MODULE_NAME_root" sequence="10"/>

EXAMPLE (MODULE NAME cyllo_accounting)

.. code-block::xml

    <menuitem id="menu_cyllo_accounting_root" sequence="10"/>

CATEGORY MENU (With parent and without action)

.. code-block::xml

    <menuitem id="menu_string_categ" sequence="10" parent="parent menu id"/>

EXAMPLE (Category menu name is Accounting)

.. code-block::xml

    <menuitem id="menu_accounting_categ" sequence="10" parent="cyllo_accounting.menu_cyllo_accounting_root"/>

SUBMENU (With parent and action)

.. code-block::xml

    <menuitem id="menu_string" sequence="10" parent="parent categ menu id" action="external id of action"/>

EXAMPLE (Submenu name is General Ledger)

.. code-block::xml

    <menuitem id="menu_general_ledger" sequence="10" parent="cyllo_accounting.menu_accounting_categ" action="action_general_ledger"/>

Data Records
------------

Use the following pattern, where `<model_name>` is the name of the model that
the record is an instance of: `<model_name>_<record_name>`

.. code-block:: xml

    <record id="res_users_important_person" model="res.users">
        ...
    </record>

Demo Records
------------

Preffix all demo record XML IDs with `demo`. This allows them to be easily
distinguished from regular records, which otherwise requires examining the
source or reinstalling the module with demo data disabled.

.. code-block:: xml

    <record id="demo_res_users_not_a_real_user" model="res.users">
        ...
    </record>

******
Python
******

PEP8 options
============

Using the linter flake8 can help to see syntax and semantic warnings or errors.
Project Source Code should adhere to PEP8 and PyFlakes standards with
a few exceptions:

* In `__init__.py` only

  *  F401: `module` imported but unused

Imports
=======

The imports are ordered as

1. Standard library imports
2. Known third party imports (One per line sorted and split in python stdlib)
3. Odoo imports (`odoo`)
4. Imports from Odoo modules (rarely, and only if necessary)
5. Local imports in the relative form
6. Unknown third party imports (One per line sorted and split in python stdlib)

Inside these 6 groups, the imported lines are alphabetically sorted.

.. code-block:: python

    # 1: imports of python lib
    import base64
    import logging
    import re
    import time

    # 2: import of known third party lib
    import lxml

    # 3:  imports of odoo
    import odoo
    from odoo import api, fields, models  # alphabetically ordered
    from odoo.tools.safe_eval import safe_eval
    from odoo.tools.translate import _

    # 4:  imports from odoo modules
    from odoo.addons.website.models.website import slug
    from odoo.addons.web.controllers.main import login_redirect

    # 5: local imports
    from . import utils

    # 6: Import of unknown third party lib
    _logger = logging.getLogger(__name__)
    try:
        import external_dependency_python_N
    except ImportError:
        _logger.debug('Cannot `import external_dependency_python_N`.')

* Note:

  * You can use
    `isort <https://pypi.python.org/pypi/isort/>`_
    to automatically sort imports.
  * Install with `pip install isort` and use with `isort myfile.py`.

Idioms
======

* Prefer `%` over `.format()`, prefer `%(varname)` instead of positional.
  This is better for translation
  `and security <https://github.com/OCA/pylint-odoo/issues/302#issue-758472967>`__.
* Always favor **Readability** over **conciseness** or using the language
  features or idioms.
* Use list comprehension, dict comprehension, and basic manipulation using
  `map`, `filter`, `sum`, ... They make the code more pythonic, easier to read
  and are generally more efficient
* The same applies for recordset methods: use `filtered`, `mapped`, `sorted`,
  ...
* Exceptions: Use `from odoo.exceptions import Warning as UserError` (v8)
  or `from odoo.exceptions import UserError` (as of v9)
  or find a more appropriate exception in `odoo.exceptions.py`
* Document your code

  * Docstring on methods should explain the purpose of a function,
    not a summary of the code
  * Simple comments for parts of code which do things which are not
    immediately obvious
  * Too many comments are usually a sign that the code is unreadable and
    needs to be refactored

* Use meaningful variable/class/method names
* If a function is too long or too indented due to loops, this is a sign
  that it needs to be refactored into smaller functions
* If a function call, dictionary, list or tuple is broken into two lines,
  break it at the opening symbol. This adds a four space indent to the next
  line instead of starting the next line at the opening symbol.

  Example:

  .. code-block:: python

    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required="1",
    )

* When making a comma separated list, dict, tuple, ... with one element per
  line, append a comma to the last element. This makes it so the next element
  added only changes one line in the changeset instead of changing the last
  element to simply add a comma.
* If an argument to a function call is not immediately obvious, prefer using
  named parameter.
* Use English variable names and write comments in English. Strings which need
  to be displayed in other languages should be translated using the translation
  system

Symbols
=======

Cyllo Python Classes
-------------------

Use UpperCamelCase.

.. code-block:: python

    class AccountMove(models.Model):
        ...


Variable names
--------------

* Always give your variables a meaningful name. You may know what it's
  referring to now, but you won't in 2 months, and others don't either.
  One-letter variables are acceptable only in lambda expressions and loop
  indices, or perhaps in pure maths expressions (and even there it doesn't hurt
  to use a real name).

.. code-block:: python

    # unclear and misleading
    a = {}
    sfields = {}

    # better
    results = {}
    selected_fields = {}

* Use underscore lowercase notation for common variables (snake_case)
* Since new API works with records or recordsets instead of id lists, don't
  suffix variable names with `_id` or `_ids` if they do not contain an ids or
  lists of ids.

  .. code-block:: python

    res_partner = self.env['res.partner']
    partners = res_partner.browse(ids)
    partner_id = partners[0].id

* Use underscore uppercase notation for global variables or constants

  .. code-block:: python

    CONSTANT_VAR1 = 'Value'
    ...
    class ...
    ...


SQL
===

No SQL Injection
----------------

Care must be taken not to introduce SQL injections vulnerabilities when using manual SQL queries. The vulnerability is present when user input is either incorrectly filtered or badly quoted, allowing an attacker to introduce undesirable clauses to a SQL query (such as circumventing filters or executing **UPDATE** or **DELETE** commands).

The best way to be safe is to never, NEVER use Python string concatenation (+) or string parameters interpolation (%) to pass variables to a SQL query string.

The second reason, which is almost as important, is that it is the job of the database abstraction layer (psycopg2) to decide how to format query parameters, not your job! For example psycopg2 knows that when you pass a list of values it needs to format them as a comma-separated list, enclosed in parentheses!

.. code-block:: python

    # the following is very bad:
    #   - it's a SQL injection vulnerability
    #   - it's unreadable
    #   - it's not your job to format the list of ids
    cr.execute('select distinct child_id from account_account_consol_rel ' +
               'where parent_id in ('+','.join(map(str, ids))+')')

    # better
    cr.execute('SELECT DISTINCT child_id '\
               'FROM account_account_consol_rel '\
               'WHERE parent_id IN %s',
               (tuple(ids),))

This is very important, so please be careful also when refactoring, and most importantly do not copy these patterns!

Models
======

* Model names

  * Use dot lowercase name for models. Example: `sale.order`
  * Use name in a singular form. `sale.order` instead of `sale.orders`

* Method conventions

  * Compute Field: the compute method pattern is `_compute_<field_name>`
  * Inverse method: the inverse method pattern is `_inverse_<field_name>`
  * Search method: the search method pattern is `_search_<field_name>`
  * Default method: the default method pattern is `_default_<field_name>`
  * Onchange method: the onchange method pattern is `_onchange_<field_name>`
  * Constraint method: the constraint method pattern is
    `_check_<constraint_name>`
  * Action method: an object action method is prefix with `action_`.

* In a Model attribute order should be

  #. Private attributes (`_name`, `_description`, `_inherit`, ...)
  #. Fields declarations
  #. SQL constraints
  #. Default method and `_default_get`
  #. Compute and search methods in the same order than field declaration
  #. Constrains methods (`@api.constrains`) and onchange methods
     (`@api.onchange`)
  #. CRUD methods (ORM overrides)
  #. Action methods
  #. And finally, other business methods.

.. code-block:: python

    class Event(models.Model):
        # Private attributes
        _name = 'event.event'
        _description = 'Event'

        # Fields declaration
        name = fields.Char(default=lambda self: self._default_name())
        seats_reserved = fields.Integer(
            string='Reserved Seats',
            store=True,
            readonly=True,
            compute='_compute_seats',
        )
        seats_available = fields.Integer(
            string='Available Seats',
            store=True,
            readonly=True,
            compute='_compute_seats',
        )
        price = fields.Integer(string='Price')

        # SQL constraints
        _sql_constraints = [
            ('name_uniq', 'unique(name)', 'Name must be unique'),
        ]

        # Default methods
        def _default_name(self):
            ...

        # compute and search fields, in the same order that fields declaration
        @api.depends('seats_max', 'registration_ids.state')
        def _compute_seats(self):
            ...

        # Constraints and onchanges
        @api.constrains('seats_max', 'seats_available')
        def _check_seats_limit(self):
            ...

        @api.onchange('date_begin')
        def _onchange_date_begin(self):
            ...

        # CRUD methods
        def create(self):
            ...

        # Action methods
        def action_validate(self):
            self.ensure_one()
            ...

        # Business methods
        def mail_user_confirm(self):
            ...

Fields
======

* `One2Many` and `Many2Many` fields should always have `_ids` as suffix
  (example: sale_order_line_ids)
* `Many2One` fields should have `_id` as suffix
  (example: partner_id, user_id, ...)
* If the technical name of the field (the variable name) is the same to the
  string of the label, don't put `string` parameter for new API fields, because
  it's automatically taken. If your variable name contains "_" in the name,
  they are converted to spaces when creating the automatic string and each word
  is capitalized.
  (example:

      old api `'name': fields.char('Name', ...)`
      new api `'name': fields.Char(...)`)

* Default functions should be declared with a lambda call on self. The reason
  for this is so a default function can be inherited. Assigning a function
  pointer directly to the `default` parameter does not allow for inheritance.

  .. code-block:: python

      a_field(..., default=lambda self: self._default_get())

Exceptions
==========

The `pass` into block except is not a good practice!

By including the `pass` we assume that our algorithm can continue to function
after the exception occurred

If you really need to use the `pass` consider logging that exception

.. code-block:: python

    try:
        sentences
    except Exception:
        _logger.debug('Why the exception is safe....', exc_info=1))


***
CSS
***

* Prefix all your classes with `o_<module_name>` where `module_name` is the
  technical name of the module (`sale`, `im_chat`, ...) or the main route
  reserved by the module (for website module mainly,
  i.e. `o_forum` for website_forum module). The only exception for this rule is
  the webclient: it simply use `o_` prefix.
* Avoid using ids
* Use bootstrap native classes
* Use underscore lowercase notation to name classes

*****
Tests
*****

As a general rule, a bug fix should come with a unittest which would fail
without the fix itself. This is to assure that regression will not happen in
the future. It also is a good way to show that the fix works in all cases.

New modules or additions should ideally test all the functions defined. The
coveralls utility will comment on pull requests indicating if coverage
increased or decreased. If it has decreased, this is usually a sign that a test
should be added. The coveralls web interface can also show which lines need
test cases.

**NOTE:** if you add an example module to showcase modules' features
you should name it ``module_name_example`` (ie: `cms_form` and `cms_form_example`).
In this way coverage analysis will ignore this extra module by default.


***
Git
***

Commit message
==============

Write a **short** commit summary without prefixing it. It should not be longer than
50 characters: `This is a commit message`

Then, in the message itself, specify the part of the code impacted by your
changes (module name, lib, transversal object, ...) and a description of the
changes. This part should be multiple lines no longer than 80 characters.

* Commit messages are in English
* Merge proposals should follow the same rules as the title of the propsal is
  the first line of the merge commit and the description corresponds to commit
  description.
* Always put meaningful commit messages: commit messages should be
  self explanatory (long enough) including the name of the module that
  has been changed and the reason behind that change. Do not use
  single words like "bugfix" or "improvements".
* Avoid commits which simultaneously impact lots of modules. Try to
  split into different commits where impacted modules are different.
  This is helpful if we need to revert changes on a module separately.
* Only make a single commit per logical change set. Do not add commits such as
  "Fix pep8", "Code review" or "Add unittest" if they fix commits which are
  being proposed
* Use present imperative (Fix formatting, Remove unused field) avoid appending
  's' to verbs: Fixes, Removes


.. code-block::

    [IMP] module_name: add module system to the web client
    [FIX] module_name: fixed the issue of reloading
    [UPDT] module_name: updated the style of status bar
    [RMV] module_name: removed company logo from navbar
    [CHG] module_name: changed navbar color

******
Github
******

Repositories
============

* Repository name is cyllo

Naming
------

* Project name must not contain `odoo` or `openerp`.
* Project name for localization is `l10n-belgium` for Belgium.
* Project name for connectors is `connector-magento` for Magento connector.

****************
Additional Facts
****************

Logical Thinking
================

* Always check the file, class, model, record naming before committing the modules.
* Use optional="hide" / optional="hide" in list views according to use case.
* Use multi_edit="1" in list views if required.
* Give proper title and description to window actions(Do not use "Create New Document")
* Give proper conditions for unlinking records according to logic.
* Give depends to only required modules.
* Give proper accessrights, record rules and permissions.
* Make sure you have tested module with at least 3 user roles before committing.
* Make sure all points in the guidelines are meet before committing.

