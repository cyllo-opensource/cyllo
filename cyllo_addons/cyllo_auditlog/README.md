Cyllo Audit Log
---------------

The Cyllo <a href="https://www.cyllo.com/auditlog">Audit Log</a> app lets administrators
track create, update, delete, and read activity across any business model with
configurable, company-aware audit rules. Every event captures who did what,
when, and from where, giving you full traceability of changes in your Cyllo database.

Rule-Based Auditing Per Model
-----------------------------

Define an audit rule for any non-transient model and choose exactly which
operations to record: create, update, delete, and optionally read. Rules carry
a sequence, an active toggle, and a log level (Info, Warning, or Critical) that
is inherited by every log they generate.

Field-Level Change Tracking
---------------------------

Control tracking scope per rule to record all fields, only a selected set of
tracked fields, or every field except an excluded list. Update events store
field-by-field before-and-after values, including readable descriptions of
many2one, many2many, and one2many changes.

User And Group Based Filtering
------------------------------

Target auditing precisely by including all users, specific users, everyone
except selected users, or the members of chosen groups. An advanced user domain
filter and a computed count of affected users make it easy to see the reach of
each rule.

Session And HTTP Request Logging
--------------------------------

Optionally link each log entry to the user's audit session and the originating
HTTP request, capturing the session ID, IP address, user agent, request path,
and URL. This connects individual data changes back to the exact browser session
and web request that produced them.

Retention Policy And Cleanup
----------------------------

Enable a per-rule retention policy to keep logs only for a configured number of
days, with a scheduled action that automatically removes expired entries. A
manual cleanup action is also available to purge all logs tied to a specific rule
on demand.

Multi-Company Visibility Control
--------------------------------

Rules are company-specific, and auditing evaluates only the rules that belong to
the active company or that apply to all companies. This keeps audit trails
correctly scoped in multi-company Cyllo environments while a dedicated reporting
view lets you review and analyze the collected logs.
