Cyllo Approval
--------------

The Cyllo <a href="https://www.cyllo.com/approval">Approval</a> app lets you require sign-off before critical
actions are carried out on any record. Define approval rules on the models you choose and Cyllo automatically
intercepts the action, raising an approval request that must be granted before the operation can proceed.

Flexible Approval Rules
-----------------------

Configure rules that trigger on a button click, on a state or stage change, or on the run of a server action.
Rules are bound to a target model and can be narrowed further with a Python domain, so approval is only
enforced on the records that actually match your conditions.

Approval Requests Workflow
--------------------------

Every triggered rule creates an Approval Request with its own sequence reference that moves through Pending,
Approved and Rejected states. Requests are logged against the source document, tracked in the chatter, and
can be reopened directly from the request to review the record awaiting a decision.

Approvers and Multi-Level Sequencing
------------------------------------

Build the whole approval chain inside a single rule: the Approval Levels tab holds one line per level, each
with its own sequence and its own approver or approver group. The lowest sequence is requested first and,
as soon as it is approved, Cyllo asks the next level automatically - nobody has to click the original button
again to move the chain forward. Once the last level says yes, the action the approval was requested for is
replayed on behalf of the requester: the button runs, or the state change is applied. Turn off Execute on
Final Approval on the rule if you would rather have the requester trigger it again themselves. A rejection
closes the cycle, so the next attempt starts over from the first level.

In-Form Approval Actions
------------------------

Approve, Reject, Request Approval and Transfer buttons are injected dynamically into the target document's
form view, along with a stat button showing the number of related requests. Approvers act right where they
work, and a warning banner reminds users when a state change is blocked pending approval.

Transfer and Comments
---------------------

The current approver can hand a request over to another user through the transfer wizard, recording a
mandatory reason in the chatter. Rules can also allow the requester to attach a private comment to the
document when submitting a request.

Email Notifications
-------------------

Enable email alerts per rule to notify the approver when a request is created and the requester when a
request is approved or rejected. Notifications are driven by dedicated Cyllo mail templates, keeping everyone
informed as the approval progresses.
