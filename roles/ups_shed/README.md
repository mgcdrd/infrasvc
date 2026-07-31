ups_shed
========

Threshold-polling tiered shutdown logic for the UPS monitoring project.
Deploys a systemd timer that polls `battery.charge` while the UPS is on
battery, and runs whichever tier(s) of a staged shutdown it has newly
crossed — k8s worker drain, then per-host `poweroff` over SSH, then the
hypervisor those hosts ran on.

Companion to `mgcdrd.infrasvc.nut_client` (which owns the actual NUT
`upsmon` config) and `mgcdrd.infrasvc.nut_server` — install both, this
role's job starts where theirs stops. Design and rationale:
wiki `enterpriseServices/Power/UPS_NUT_Monitoring`.

Tested on: Debian 12/13, Rocky Linux 9/10 (EL via EPEL). Not yet run
against real hardware — never triggered by an actual outage yet, and
deliberately not tested by forcing a real poweroff during development.


Requirements
------------

`become: true` and `gather_facts: true` are required. Needs `ansible-core`,
`jq`, and `kubectl` on the target host — all installed by this role.

Requires the `svc-ups-shutdown` identity already built (IPA account, SSH
key, sudo/HBAC rules, Vault AppRole, k8s RBAC) — this role only consumes
it, doesn't create it. See the design doc's "Auth model" section.


How it fires
------------

1. `mgcdrd.infrasvc.nut_client`'s NOTIFYCMD script calls this role's
   `ups-shed-notify-hook.sh` (wired via `nut_client_notify_hook`) on every
   NUT event.
2. On `ONBATT`, the hook starts `ups-shed-check.timer` — inert until then,
   not enabled at boot.
3. Every `ups_shed_poll_interval` seconds, `ups-shed-check.sh` reads
   `battery.charge` via `upsc` and compares it against the three
   thresholds, in ascending order, tracking the deepest tier already run
   in `{{ ups_shed_state_dir }}/state` so nothing re-fires.
4. Crossing a threshold runs `ups-shed-run-tier.sh <tierN>`:
   - **tier1**: cordon+drain `ups_shed_k8s_workers` via the k8s API (token
     fetched fresh from Vault, never cached to disk), then `poweroff`
     `ups_shed_tier1_guests` over SSH, wait `ups_shed_graceful_wait`
     seconds, then `poweroff` `ups_shed_tier1_hypervisor`.
   - **tier2**: same shape as tier1, no k8s drain step.
   - **tier3**: alert-only, logged, no poweroff — matches the design's
     "never auto-shed past this point" tier.
5. On `ONLINE`, the hook stops the timer and resets state to 0.

Nothing runs until a real `ONBATT` event. Deploying this role has no
effect on a system with stable power.


Role Variables
---------------

All variables are prefixed `ups_shed_`. See `defaults/main.yml` for the
full list — host lists default empty, thresholds default to 70/40/20.

```yaml
ups_shed_ups_name: apc
ups_shed_ups_host: deluge.lab.provenzawt.dev

ups_shed_k8s_workers:
  - kube2.lab.provenzawt.dev
  - kube3.lab.provenzawt.dev

ups_shed_tier1_guests:
  - runner1.lab.provenzawt.dev
  - foreman2.lab.provenzawt.dev
ups_shed_tier1_hypervisor: pve3.lab.provenzawt.dev

ups_shed_tier2_guests:
  - dns2.lab.provenzawt.dev
  - ipa3.lab.provenzawt.dev
ups_shed_tier2_hypervisor: pve4.lab.provenzawt.dev
```

`ups_shed_tier1_hypervisor`/`ups_shed_tier2_hypervisor` are each a single
host, not a list — one hypervisor per tier in this design. Leave empty
(`""`) if a tier has no hypervisor to power off.


Example Playbook
-----------------

```yaml
- name: UPS shed logic
  hosts: nut_client
  gather_facts: true
  become: true
  roles:
    - mgcdrd.infrasvc.nut_client
    - mgcdrd.infrasvc.ups_shed
  vars:
    nut_client_notify_hook: /usr/local/bin/ups-shed-notify-hook.sh
    ups_shed_ups_host: deluge.lab.provenzawt.dev
    # ... tier host lists ...
```


Notes
-----

- **k8s auth is a static token, not dynamically issued.** This Vault
  instance doesn't have a Kubernetes secrets engine mounted, so
  `k8s_drain_token` in Vault (`infra/lab/ups-shutdown`) is a long-lived
  ServiceAccount token rather than something minted per-use. Read fresh
  from Vault on every drain, never written to disk. Upgrading to dynamic
  issuance is a clean future improvement, not required for this to work.
- **`--insecure-skip-tls-verify`** on the k8s drain calls avoids needing
  to distribute the cluster CA bundle to the responder VM — a deliberate
  simplification, reasonable for an internal-only API endpoint.
- **Recovery isn't automated.** `ONLINE` only stops the timer and resets
  state — bringing shed hosts back up (power-on order, uncordoning k8s
  nodes, health verification) is manual. Flagged as explicit future work
  in the design doc, not an oversight.
- **`poweroff` is fired async/`poll:0` with errors ignored** in the shed
  playbook — the SSH connection it runs over drops as the host powers
  off, which looks like a task failure to Ansible even though the command
  worked. That's expected, not a bug.
- **Not yet exercised against a real outage.** Every piece (NUT triggers,
  Vault AppRole, sudo/HBAC scope, k8s RBAC) has been verified independently,
  but the full chain firing end-to-end from a real `ONBATT` event hasn't
  happened yet.


License
-------

GPL-3.0-or-later
