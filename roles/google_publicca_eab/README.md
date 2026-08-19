google_publicca_eab
====================

Mints a Google Cloud Public CA external account binding (EAB) key on
demand via `gcloud publicca external-account-keys create`, and writes the
result to HashiCorp Vault so an ACME client (e.g.
[`mgcdrd.infrabase.acme_sh`](../../../infrabase/roles/acme_sh)) can
register or recover an ACME account with Google's Public CA.

This role only calls the GCP API and Vault — it never touches a managed
host's OS, so it runs entirely against the control node (`delegate_to:
localhost` internally). Include it in a play targeting the real
consuming host so `google_publicca_eab_account_name` defaults to a
meaningful value; the role itself does nothing on that host.


Why this exists
----------------

Google Public CA EAB keys are **single-use**: one key registers exactly
one ACME account and is invalidated the moment it's used. An unused key
expires after 7 days. A registered ACME account itself never expires.

That means:

- **Don't** treat a Vault-stored EAB key as a normal long-lived secret to
  read and reuse — once an ACME client has registered with it, the value
  in Vault is dead. Keeping it around is harmless (for the 7-day audit
  trail) but it can't be replayed.
- **Don't** share one Vault path across multiple hosts/accounts. Each
  host/ACME-account needing to register with Google needs its own
  freshly minted key, at its own Vault path.
- This role is **on-demand**, not idempotent against Vault state. Run it
  explicitly when standing up a new host that will register with Google
  Public CA, or recovering a host that lost its local acme.sh account
  state (e.g. `/root/.acme.sh` wiped by a rebuild) — never as a routine
  step in every deployment run.
- Because of the 7-day expiry, run this role and the consuming acme.sh
  registration in the same operation (or close together) rather than
  minting a key far in advance.


Requirements
------------

- `gcloud` CLI installed and on `PATH` on the control node.
- A GCP service-account JSON key with the **Public CA External Account
  Key Creator** role (`roles/publicca.externalAccountKeyCreator`) on the
  target project.
- A Vault token or AppRole (`ANSIBLE_HASHI_VAULT_*` env vars) with write
  access to the destination KV path — `community.hashi_vault` module
  tasks don't inherit `ANSIBLE_HASHI_VAULT_*` declaratively, so this role
  passes them through explicitly (see `generate.yml`).


Role Variables
---------------

### GCP

```yaml
google_publicca_eab_project: ""          # GCP project ID — required
google_publicca_eab_gcp_sa_json: ""      # GCP service-account JSON key content — required
                                          # e.g. "{{ vault_google_sa_json }}"
```

The service-account JSON is written to a `mode: "0600"` temp file only
for the duration of the `gcloud` call (`GOOGLE_APPLICATION_CREDENTIALS`),
then shredded — never persisted on the control node.

### Account

```yaml
google_publicca_eab_account_name: "{{ inventory_hostname }}"
```

A label, not passed to `gcloud` — used only to compose the Vault path
below and to tag the stored secret so it's traceable to what it was
minted for.

### Vault (write destination)

```yaml
google_publicca_eab_vault_addr:     ""   # e.g. "{{ vault_addr }}"
google_publicca_eab_vault_kv_mount: ""   # e.g. "{{ vault_kv_infra_mount }}"
google_publicca_eab_vault_path:     ""   # full KV path — required, compose explicitly:
                                          # "{{ vault_kv_env }}/acme/google/{{ google_publicca_eab_account_name }}"
```

Writes `kid`, `hmac_key`, `account_name`, and `created_at` to that path.


Example Playbook
-----------------

```yaml
- name: Mint a Google Public CA EAB key for a new Foreman host
  hosts: foreman
  gather_facts: false
  roles:
    - role: mgcdrd.infrasvc.google_publicca_eab
      vars:
        google_publicca_eab_project: "acme-lab-pki"
        google_publicca_eab_gcp_sa_json: "{{ vault_google_sa_json }}"
        google_publicca_eab_vault_addr: "{{ vault_addr }}"
        google_publicca_eab_vault_kv_mount: "{{ vault_kv_infra_mount }}"
        google_publicca_eab_vault_path: "{{ vault_kv_env }}/acme/google/{{ inventory_hostname }}"
```

Then, in the same or a follow-up run, feed the freshly written path into
`acme_sh`:

```yaml
acme_sh_ca: google
acme_sh_eab_enabled: true
acme_sh_eab_kid:      "{{ lookup('community.hashi_vault.vault_kv2_get', vault_kv_env + '/acme/google/' + inventory_hostname, engine_mount_point=vault_kv_infra_mount, url=vault_addr).secret.kid }}"
acme_sh_eab_hmac_key: "{{ lookup('community.hashi_vault.vault_kv2_get', vault_kv_env + '/acme/google/' + inventory_hostname, engine_mount_point=vault_kv_infra_mount, url=vault_addr).secret.hmac_key }}"
```

Once `acme_sh` has registered the account, EAB vars are no longer
needed — see `acme_sh`'s README.


Recovery
--------

If a host's local acme.sh state is lost (rebuild, disk loss) and it was
using Google Public CA, its old ACME account is gone with it — the old
EAB key that created it was already consumed and can't be reused. Run
this role again with the same `google_publicca_eab_account_name` (it'll
just overwrite the dead Vault entry with a fresh one), then re-run
`acme_sh` to register a new account and re-issue certs.
