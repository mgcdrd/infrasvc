keepalived
==========

Installs and configures keepalived with VRRP instances, preset health-check
scripts, and automatic node priority calculation.

Supports multi-node clusters. The master node receives `keepalived_priority_max`
(210) and priorities are spread linearly down to `keepalived_priority_min` (90)
across backup nodes. Existing VRRP auth passwords are preserved across runs by
reading the current config before writing.

Tested on: Debian 12/13, Rocky Linux 9/10


Requirements
------------

`become: true` and `gather_facts: true` are required. The priority calculation
uses `ansible_default_ipv4.interface` and `hostvars` for unicast peer addresses,
so all nodes in the play must be reachable.


Presets
-------

Presets bundle a health-check script template with a `vrrp_script` definition.
Set `keepalived_vip_for` to activate one or more presets:

| Preset | Script placed on host | Checks |
|--------|-----------------------|--------|
| `webproxy` | `/etc/keepalived/check_nginx.sh` | nginx process |
| `ftp` | `/etc/keepalived/check_haproxy.sh` | haproxy process |
| `kubernetes` | `/etc/keepalived/check_apiserver.sh` | k8s API server |
| `dockerswarm` | `check_node_active.sh`, `check_node_ready.sh` | swarm node state |

Each preset's `vrrp_script` block is included in the config and all instances
track it by default. Override per-instance with `vrrp_scripts.presets`.


Role Variables
--------------

### Required

```yaml
keepalived_vip_for:          # list of preset names to activate
  - webproxy

keepalived_vrrp_instances:   # list of VRRP instances
  - name: VI_WEB
    master_node: node1.example.com
    backup_nodes:
      - node2.example.com
    virt_ip:
      - 192.168.1.100/24
```

### Priority tuning

```yaml
keepalived_priority_max: 210   # priority assigned to master node
keepalived_priority_min: 90    # priority assigned to last backup node
```

### Global defs (optional)

```yaml
keepalived_global_defs:
  vrrp_startup_delay: 5
  notification_email_from: keepalived@example.com
  smtp_server: smtp.example.com
  smtp_connect_timeout: 10
```

### Extra VRRP scripts (optional)

Scripts beyond what the chosen presets provide:

```yaml
keepalived_vrrp_scripts:
  - name:      check_custom
    script:    /etc/keepalived/check_custom.sh
    template:  custom/check_custom.sh.j2
    interval:  3
    user:      root
    group:     root
    weight:    26
    fall:      3
    rise:      4
    init_fail: true
```

### VRRP instance fields

```yaml
keepalived_vrrp_instances:
  - name: VI_WEB              # vrrp_instance block name
    master_node: node1        # inventory hostname of the master
    backup_nodes:             # list of backup inventory hostnames
      - node2
      - node3
    interface: eth0           # optional — defaults to ansible_default_ipv4.interface
    virtual_router_id: 51     # optional — auto-derived from VIP octets if omitted
    smtp_alert: true          # optional — emit SMTP alerts on state changes
    virt_ip:
      - 192.168.1.100/24
    vrrp_scripts:             # optional — override which scripts this instance tracks
      presets:
        - webproxy
      extra:
        - check_custom
    notify_master: /etc/keepalived/notify_master.sh   # optional
    notify_backup: /etc/keepalived/notify_backup.sh   # optional
    notify_fault:  /etc/keepalived/notify_fault.sh    # optional
```

### VRRP script defaults

Applied to preset and extra scripts that omit the field:

```yaml
vrrp_script_interval: 3
vrrp_script_fall: 3
vrrp_script_rise: 4
vrrp_script_init_fail: true
vrrp_script_user: root
vrrp_script_group: root
```


Example Playbook
----------------

**Two-node web proxy cluster:**

```yaml
- name: Configure keepalived
  hosts: proxy_cluster
  gather_facts: true
  become: true
  roles:
    - mgcdrd.infrasvc.keepalived
  vars:
    keepalived_vip_for:
      - webproxy

    keepalived_vrrp_instances:
      - name: VI_PROXY
        master_node: proxy1.example.com
        backup_nodes:
          - proxy2.example.com
        virt_ip:
          - 10.0.1.10/24

- name: Configure keepalived
  hosts: ftp_cluster
  gather_facts: true
  become: true
  roles:
    - mgcdrd.infrasvc.keepalived
  vars:
    keepalived_vip_for:
      - ftp

    keepalived_vrrp_instances:
      - name: VI_FTP
        master_node: ftp1.example.com
        backup_nodes:
          - ftp2.example.com
          - ftp3.example.com
        virt_ip:
          - 10.0.2.10/24
```


Notes
-----

- **Auth password**: On first run a deterministic password is generated from
  `sha1(instance_name + '-' + master_node)` truncated to 8 characters. On
  subsequent runs the existing password is read from the config and preserved,
  so re-keying never happens accidentally.
- **Unicast peers**: The role configures `unicast_peer` blocks using
  `ansible_default_ipv4.address` from each node's hostvars. All nodes in the
  play must be present in the same inventory run.
- **`virtual_router_id` auto-derivation**: If omitted, the VRID is calculated
  as `(third_octet + fourth_octet) % 100` from the first VIP. Must be unique
  per subnet — set explicitly if auto-generated values collide.


License
-------

GPL-3.0-or-later
