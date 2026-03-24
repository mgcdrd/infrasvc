phpipam_config
==============

Configures a phpIPAM instance via its REST API. Manages the full set of
phpIPAM objects needed to describe a network environment — customers, sections,
VLANs, nameservers, NAT policies, locations, racks, subnets, IP address
assignments, devices, and circuits — all from Ansible vars with full idempotency.

Intended as the Day 1 companion to `mgcdrd.infrasvc.pdns_phpipam`, running after
the stack is deployed to seed the IPAM with your environment's structure.

Tested on: Debian 12/13, Rocky Linux 9/10


Requirements
------------

**phpIPAM API application must be pre-configured** before this role can run.
In phpIPAM: `Administration > API > Create API key`

- App ID: must match `phpipam_config_app_id` (default: `ansible`)
- App permissions: Read/Write
- App security: SSL with App Code, or User token (role uses user token auth)

`gather_facts` and `become` are **not** required — all work is via the API.


Object Ordering
---------------

Objects are created in dependency order. You do not need to manage ordering
in your vars — the role handles it:

```
customers → sections → vlans → nameservers → nat → locations
  → racks (needs locations)
  → subnets (needs sections, vlans, nameservers, customers)
    → addresses (needs subnet IDs)
  → devices (needs locations, racks)
  → circuits
```


Role Variables
--------------

### Required

```yaml
phpipam_config_url:      "http://127.0.0.1"   # phpIPAM base URL
phpipam_config_app_id:   "ansible"            # API app ID from phpIPAM admin
phpipam_config_username: ""                   # phpIPAM username — use Vault
phpipam_config_password: ""                   # phpIPAM password — use Vault
```

### Customers

```yaml
phpipam_config_customers:
  - name: "Acme Corp"
    description: "Primary customer"
    contact: "Admin"
    email: "admin@acme.com"
    phone: ""
    state: present       # present (default) or absent
```

### Sections

```yaml
phpipam_config_sections:
  - name: "Lab"
    description: "Lab networks"
    strictMode: false    # enforce strict subnet boundaries (default: false)
    state: present
```

### VLANs

```yaml
phpipam_config_vlans:
  - name: "Management"
    number: 10
    description: "Management VLAN"
    l2domain: "Default"  # L2 domain name (optional — uses default if omitted)
    state: present
```

### Nameservers

```yaml
phpipam_config_nameservers:
  - name: "Lab DNS"
    nameserver1: "10.100.14.53"
    nameserver2: ""      # optional
    nameserver3: ""      # optional
    description: "Primary lab DNS"
    state: present
```

### NAT Policies

```yaml
phpipam_config_nat:
  - name: "Lab NAT"
    type: "1-to-1"       # "1-to-1" (default) or "many-to-1"
    description: ""
    state: present
```

### Locations

```yaml
phpipam_config_locations:
  - name: "Home Lab"
    description: "Home rack room"
    address: ""
    state: present
```

### Racks

```yaml
phpipam_config_racks:
  - name: "Main Rack"
    size: 42             # rack units (default: 42)
    location: "Home Lab" # location name (optional)
    description: ""
    state: present
```

### Subnets and Address Assignments

```yaml
phpipam_config_subnets:
  - subnet: "10.100.10.0"
    mask: 24
    section: "Lab"               # section name (required)
    description: "Lab network"
    vlan: "Management"           # VLAN name (optional)
    nameserver: "Lab DNS"        # nameserver set name (optional)
    customer: "Acme Corp"        # customer name (optional)
    pingSubnet: false
    discoverSubnet: false
    state: present
    addresses:
      - ip: "10.100.10.1"
        hostname: "vault.lab.example.com"
        description: "Vault server"
        tag: 2                   # 1=Offline 2=Used(default) 3=Reserved 4=DHCP 5=Gateway
        mac: ""                  # optional
        owner: ""                # optional
        note: ""                 # optional
        state: present
      - ip: "10.100.10.254"
        hostname: "gateway.lab.example.com"
        tag: 5                   # Gateway
        state: present
```

### Devices

```yaml
phpipam_config_devices:
  - hostname: "pve2.lab.example.com"
    ip: "10.100.10.101"
    description: "Proxmox node 2"
    type: 1              # phpIPAM device type ID (optional)
    location: "Home Lab" # location name (optional)
    rack: "Main Rack"    # rack name (optional)
    rack_start: 1        # starting rack unit (optional)
    rack_size: 2         # rack units occupied (optional)
    state: present
```

### Circuits

```yaml
phpipam_config_circuits:
  - name: "ISP Uplink"
    cid: "CIR-001"
    description: ""
    state: present
```


Example Playbook
----------------

**Seed phpIPAM after deploying the pdns_phpipam stack:**

```yaml
- name: Deploy PowerDNS + phpIPAM
  hosts: dns_servers
  gather_facts: true
  become: true
  roles:
    - mgcdrd.infrabase.docker
    - mgcdrd.infrasvc.pdns_phpipam

- name: Configure DNS records
  hosts: dns_servers
  gather_facts: false
  become: false
  roles:
    - mgcdrd.infrasvc.pdns_records
  vars:
    pdns_records_api_url: "http://127.0.0.1:8081"
    pdns_records_api_key: "{{ vault_pdns_auth_api_key }}"
    pdns_records_zones: [...]
    pdns_records: [...]

- name: Seed phpIPAM
  hosts: dns_servers
  gather_facts: false
  become: false
  connection: local    # role makes API calls — run from the controller
  roles:
    - mgcdrd.infrasvc.phpipam_config
  vars:
    phpipam_config_url: "https://ipam.lab.example.com"
    phpipam_config_app_id: "ansible"
    phpipam_config_username: "{{ vault_phpipam_username }}"
    phpipam_config_password: "{{ vault_phpipam_password }}"
    phpipam_config_sections:
      - name: "Lab"
        description: "Lab networks"
    phpipam_config_nameservers:
      - name: "Lab DNS"
        nameserver1: "10.0.0.53"
    phpipam_config_subnets:
      - subnet: "10.100.10.0"
        mask: 24
        section: "Lab"
        nameserver: "Lab DNS"
        addresses:
          - ip: "10.100.10.1"
            hostname: "vault.lab.example.com"
            tag: 2
```


Notes
-----

- The phpIPAM API application must exist before this role runs — there is no
  way to bootstrap it automatically (chicken-and-egg with auth).
- All object lookups are by **name**. Names must be unique within their parent
  context (e.g. rack names unique within a location, subnet IPs unique within
  a section). Duplicate names will cause unexpected behaviour.
- Address updates compare hostname, description, and tag. Other fields (mac,
  owner, note) are set on create only — add PATCH logic if full update coverage
  is needed.
- Circuits API endpoint availability depends on your phpIPAM version. If the
  endpoint returns 404, disable circuits by leaving `phpipam_config_circuits`
  empty.


License
-------

GPL-3.0-or-later
