Roadmap — PESU Results Watchdog

This document tracks planned features and improvements for the project. Nothing
here is implemented yet — this is a running list of what's coming next.


Planned Features

1. Smarter handling of a slow/unresponsive Results page

Currently, if the Results page doesn't load in time, the run fails and the retry
loop starts the whole sequence over from scratch. This will be refined to
better distinguish between different failure types (e.g. page still rendering
vs. a genuine connection issue vs. a session timeout) and respond
appropriately to each, rather than treating every failure the same way.

2. Generic, reusable version (not hardcoded to one account/semester)

Right now the script is wired to one specific student's credentials and a
fixed semester. This will be generalized so that, when run, it interactively
asks for:


PESU Academy username and password
Phone number to notify
Which semester and exam (ESA/ISA, etc.) to check


This turns the project from a personal script into a reusable tool anyone
with a PESU account could run for themselves.

3. Choice between SMS and phone call notifications

Currently, notification always happens via text message through a MacroDroid
webhook. This will be extended to let the user choose, at setup time, between:


Text message (current behavior)
Phone call (e.g. a call-based alert, useful if you don't check texts
right away or want something harder to miss)


4. "Still trying" status notifications during high server traffic

When PESU's servers are under heavy load (a common occurrence right after
results are announced), page loads can fail or time out repeatedly. Instead of
retrying silently in the background, the user will get a notification letting
them know the watchdog is aware the site is struggling and is actively
continuing to retry — so it's clear the tool hasn't stalled or died, it's just
waiting out the traffic.

5. Notifications beyond SMS/call — WhatsApp, Telegram, Email

On top of SMS and calling, add support for sending the results notification
through additional channels: WhatsApp, Telegram, and email. Users will be able
to choose one or more delivery methods rather than being limited to a single
channel.

6. Support for tracking multiple students/accounts at once

Allow the watchdog to monitor results for more than one PESU account in a
single run (e.g. checking on behalf of friends too), each with their own
credentials, semester/exam selection, and notification preferences — without
needing to run entirely separate copies of the script manually.


Have a feature idea?

Open an issue describing what you'd like to see, and it can be added to this
roadmap for consideration.
