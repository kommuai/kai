# Agent-learnt FAQ (staging)

Unified diffs against `master_faq.md` are appended here after a live-agent handback (`resume`).
This file is **not** compiled into `agent_workspace/compiled/` and is **not** used during bot answers.



<!-- learn: ts=2026-05-21T16:34:26Z user_id=+60173611088 cw_conv=- truncated_master=False -->
--- a/master_faq.md
+++ b/master_faq.md
@@ -1,6 +1,6 @@
 # KOMMU MASTER FAQ (FULL REBUILD - SINGLE SOURCE OF TRUTH)
 
-Last updated: 29 Mar 2026 (install positioning: self-install encouraged)
+Last updated: 30 Mar 2026 (install positioning: self-install encouraged)
 
 # SECTION 1: INTENTS (CUSTOMER-FACING)
 
@@ -109,6 +109,18 @@
 If your car is supportable but not yet supported, you can work with us on beta support. The car usually needs to be at Kommu HQ for at least 3-5 days so we can find the right connector, run data collection, and do reverse engineering work. In return you may receive an RM300 discount (confirm current terms with sales). A live agent will coordinate schedule and technical checks.
 
+## intent: beta_followup
+aliases:
+- no one reply me
+- nobody contacted me
+- still waiting for beta reply
+- beta program follow up
+answer:
+We're sorry for the delay. I'll escalate your beta support request again right now so our team follows up with you as soon as possible. If you have a preferred contact time or method, please share it and I'll pass that along too.
+
 ## intent: rto_details
 aliases:
 - rent to own details
