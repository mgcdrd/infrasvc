pdns_records
============

Manages PowerDNS Authoritative zones and DNS records via the PowerDNS HTTP API.
Handles creating and removing zones, and creating, updating, or removing any
record type with full idempotency — re-running with no changes causes no API
calls and no `changed` events.

Intended as the Day 2 companion to `mgcdrd.infrasvc.pdns_phpipam`, but works
against any PowerDNS Authoritative server with the API enabled.

Tested on: Debian 12/13, Rocky Linux 9/10


Requirements
------------

- The PowerDNS Authoritative API must be reachable from the Ansible controller
  (or delegate host) at `pdns_records_api_url`.
- `gather_facts` is **not** required by this role.
- `become` is **not** required — all work is done via the PowerDNS HTTP API,
  not on the target host.

> **Using with pdns_phpipam?**
> The `auth` container does not expose port 8081 by default.  Either add a
> `ports` mapping to the compose file, or run this role with
> `delegate_to: localhost` and point `pdns_records_api_url` at the container's
> Docker-network IP (`pdns_phpipam_docker_network_auth`, default `10.5.0.3`).


Role Variables
--------------

### Required

```yaml
pdns_records_api_url: "http://127.0.0.1:8081"   # URL of the PowerDNS auth API
pdns_records_api_key: ""                         # API key — use Ansible Vault
```

### Optional

```yaml
# PowerDNS server ID — almost always "localhost"
pdns_records_server_id: "localhost"
```

### Zones

```yaml
pdns_records_zones:
  - name: "lab.example.com"       # trailing dot added automatically if missing
    kind: Native                  # Native (default), Master, or Slave
    nameservers:                  # required when creating a new zone
      - "ns1.lab.example.com."
    state: present                # present (default) or absent
```

### Records

```yaml
pdns_records:
  - zone: "lab.example.com"           # zone the record belongs to
    name: "host1.lab.example.com"     # FQDN — trailing dot added automatically
    type: A                           # A, AAAA, CNAME, MX, TXT, PTR, NS, SRV…
    ttl: 300                          # seconds (default: 300)
    records:                          # list of value strings for this RRset
      - "10.100.10.5"
    state: present                    # present (default) or absent
```

For record types that include a priority (MX, SRV), put the full value string
as PowerDNS expects it:

```yaml
  - zone: "lab.example.com"
    name: "lab.example.com"
    type: MX
    records:
      - "10 mail.lab.example.com."
```


How It Works
------------

### Idempotency

For **zones**, the role fetches the full zone list once per play and only calls
`POST` (create) or `DELETE` (remove) when the current state does not match the
desired state.

For **records**, the role fetches the target zone's current RRsets before each
record, extracts the matching name+type entry, and compares TTL and content
values (sorted, so order doesn't matter).  The PATCH call is skipped entirely
when nothing has changed.

### Task files

| File | What it does |
|---|---|
| `preflight.yml` | Asserts required vars; verifies API is reachable |
| `zones.yml` | Creates / removes zones based on `pdns_records_zones` |
| `records.yml` | Iterates `pdns_records`, calling `manage_record.yml` per entry |
| `manage_record.yml` | Handles a single record: normalize → fetch → compare → patch |

`manage_record.yml` is included dynamically via `include_tasks` (not
`import_tasks`) so that `set_fact` calls inside it are scoped to each
iteration and do not bleed between records.


Example Playbook
----------------

**Manage zones and records on a pdns_phpipam host:**

```yaml
- name: Configure DNS zones and records
  hosts: dns_servers
  gather_facts: false
  become: false
  roles:
    - mgcdrd.infrasvc.pdns_records
  vars:
    pdns_records_api_url: "http://127.0.0.1:8081"
    pdns_records_api_key: "{{ vault_pdns_auth_api_key }}"

    pdns_records_zones:
      - name: "lab.example.com"
        kind: Native
        nameservers:
          - "ns1.lab.example.com."
      - name: "10.100.10.in-addr.arpa"
        kind: Native
        nameservers:
          - "ns1.lab.example.com."

    pdns_records:
      - zone: "lab.example.com"
        name: "ns1.lab.example.com"
        type: A
        records:
          - "10.100.10.2"
      - zone: "lab.example.com"
        name: "host1.lab.example.com"
        type: A
        ttl: 300
        records:
          - "10.100.10.5"
      - zone: "10.100.10.in-addr.arpa"
        name: "5.10.100.10.in-addr.arpa"
        type: PTR
        records:
          - "host1.lab.example.com."
```

**Deploy the stack and then seed initial records in one play:**

```yaml
- name: Provision DNS host
  hosts: dns_servers
  gather_facts: true
  become: true
  roles:
    - mgcdrd.infrabase.docker
    - mgcdrd.infrasvc.pdns_phpipam

- name: Seed DNS records
  hosts: dns_servers
  gather_facts: false
  become: false
  roles:
    - mgcdrd.infrasvc.pdns_records
  vars:
    pdns_records_api_url: "http://127.0.0.1:8081"
    pdns_records_api_key: "{{ vault_pdns_auth_api_key }}"
    pdns_records_zones:
      - name: "lab.example.com"
        kind: Native
        nameservers:
          - "ns1.lab.example.com."
    pdns_records:
      - zone: "lab.example.com"
        name: "host1.lab.example.com"
        type: A
        records:
          - "10.100.10.5"
```


License
-------

GPL-3.0-or-later
