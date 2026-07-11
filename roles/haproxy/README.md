haproxy
=======

Installs and configures HAProxy. Generates `/etc/haproxy/haproxy.cfg` from
Ansible variables covering all standard HAProxy sections: global, defaults,
mailers, resolvers, frontends, and backends.

Sets `net.ipv4.ip_nonlocal_bind=1` via sysctl so HAProxy can bind to VIPs
managed by keepalived.

Tested on: Debian 12/13, Rocky Linux 9/10


Requirements
------------

`become: true` and `gather_facts: true` are required.

The `ansible.posix` collection must be installed (`ansible-galaxy collection
install ansible.posix`) for the sysctl task.


Role Variables
--------------

All variables are prefixed `haproxy_`. The full structure with descriptions is
in `vars/main.yml`. Common examples are shown below.

### Global section

```yaml
haproxy_global:
  logs:
    - target:   /dev/log
      facility: local0
      level:    notice
  chroot: /var/lib/haproxy   # if set, user and group are required
  user:   haproxy
  group:  haproxy
  stats:
    socket:
      - path:  /run/haproxy/admin.sock
        mode:  660
        level: admin
    raw:
      - timeout 30s
  ssl:
    dh-param-file: /etc/haproxy/dhparam.pem
  additional:
    - hard-stop-after 30s
```

### Defaults blocks

```yaml
haproxy_defaults:
  - block_name: tcp
    mode: tcp
    log:  global
    options:
      - tcplog
      - dontlognull
    timeout_connect: 5000
    timeout_client:  50000
    timeout_server:  50000
    # email_alert requires all five fields if section is present:
    email_alert:
      mailers:    mail_relays
      from:       haproxy@example.com
      to:         admin@example.com
      level:      crit
      myhostname: lb1.example.com
```

### Mailers

```yaml
haproxy_mailers:
  - block_name: mail_relays
    relays:
      - name:       smtp1
        connection: smtp1.example.com:25
```

### Resolvers

```yaml
haproxy_resolvers:
  - block_name: internal
    nameservers:
      - name:       ns1
        connection: 192.168.1.53:53
    parse_resolve_conf: false
    holds:
      valid:   10s
      nx:      30s
    timeouts:
      retry:   1s
```

### Frontends

FTP needs **two separate** frontend/backend pairs, not one frontend with two
binds sharing a backend — a single backend with a fixed `:21` on its
`server` lines would forward passive-mode data connections (which land on
whatever port in the passive range the client was told to use) to port 21
regardless, breaking every transfer:

```yaml
haproxy_frontends:
  - block_name: ftp_control
    mode: tcp
    options:
      - tcplog
    log: global
    binds:
      - 10.0.1.10:21
    default_backend: ftp_control_servers

  - block_name: ftp_data
    mode: tcp
    options:
      - tcplog
    log: global
    binds:
      - 10.0.1.10:50000-50010
    default_backend: ftp_data_servers
```

### Backends

```yaml
haproxy_backends:
  - block_name: ftp_control_servers
    mode: tcp
    balance: leastconn
    servers:
      - server1  10.0.1.101:21 init-addr none
      - server2  10.0.1.102:21 init-addr none
    additional:
      - stick-table type ip size 100k expire 1h
      - stick on src

  - block_name: ftp_data_servers
    mode: tcp
    balance: leastconn
    servers:
      # No port on these — with a ranged frontend bind, an unspecified
      # backend port makes haproxy forward each connection to whatever
      # port it arrived on. Required for the passive range to work at all.
      - server1  10.0.1.101 init-addr none
      - server2  10.0.1.102 init-addr none
```

**Stateful sessions with `balance`**: passive FTP opens control and data as
*separate* connections. If `ftp_control_servers` and `ftp_data_servers` are
balanced independently (as above, both `leastconn`), a client's control and
data connections can land on different backend servers and break the
session. The `stick-table`/`stick on src` in `ftp_control_servers` only
pins consistency *within that one backend* — making it also apply across
`ftp_data_servers` needs an explicitly shared/named stick-table between the
two, which isn't worked out here (verify the exact syntax before relying on
it). If you don't need real load spreading, active/backup (`backup` flag on
the secondary `server` line in both backends, no stick-table needed at all)
sidesteps the whole problem — see `mgcdrd.infrasvc.haproxy` used this way in
`deployments/haproxy-lb`.

### Additional files

Hard-links extra files into place before rendering the config (useful for
placing SSL bundles into a chroot):

```yaml
haproxy_additional:
  - src:   /etc/ssl/certs/bundle.pem
    dest:  /var/lib/haproxy/ssl/bundle.pem
    owner: haproxy
    group: haproxy
```


Example Playbook
----------------

```yaml
- name: Deploy HAProxy FTP load balancer
  hosts: lb_servers
  gather_facts: true
  become: true
  roles:
    - mgcdrd.infrasvc.haproxy
  vars:
    haproxy_global:
      logs:
        - target: /dev/log
          facility: local0
          level: notice
      chroot: /var/lib/haproxy
      user:   haproxy
      group:  haproxy
      stats:
        socket:
          - path:  /run/haproxy/admin.sock
            mode:  660
            level: admin
        raw:
          - timeout 30s

    haproxy_defaults:
      - block_name: tcp
        mode: tcp
        log:  global
        options:
          - tcplog
          - dontlognull
        timeout_connect: 5000
        timeout_client:  50000
        timeout_server:  50000

    haproxy_frontends:
      - block_name: ftp_control
        mode: tcp
        options:
          - tcplog
        log: global
        binds:
          - 10.0.1.10:21
        default_backend: ftp_control_servers

      - block_name: ftp_data
        mode: tcp
        options:
          - tcplog
        log: global
        binds:
          - 10.0.1.10:50000-50010
        default_backend: ftp_data_servers

    haproxy_backends:
      - block_name: ftp_control_servers
        mode: tcp
        servers:
          - ftp1  10.0.1.101:21 check
          - ftp2  10.0.1.102:21 check backup

      - block_name: ftp_data_servers
        mode: tcp
        servers:
          # No port — see the Frontends section above for why.
          - ftp1  10.0.1.101 check
          - ftp2  10.0.1.102 check backup
```

Active/backup here, matching `deployments/haproxy-lb` — see the Frontends
section above for the `balance`-with-two-backends caveat if you want real
load spreading instead.


Notes
-----

- **chroot**: If `haproxy_global.chroot` is set, `haproxy_global.user` and
  `haproxy_global.group` must also be set — the role will fail the preflight
  assert otherwise.
- **email_alert**: All five fields (`mailers`, `from`, `to`, `level`,
  `myhostname`) are required if the `email_alert` key is present in a defaults
  block. Omit the key entirely to skip email alerting.
- **Directory creation**: The role collects filesystem paths from log targets,
  socket paths, ssl cert paths, and `-f` include references in `additional`
  lines, then ensures their parent directories exist before writing the config.
- **keepalived integration**: This role pairs with `mgcdrd.infrasvc.keepalived`
  using the `ftp` preset, which deploys a check script that monitors the
  haproxy process.
- **SELinux (RedHat only)**: Sets the `haproxy_connect_any` boolean so
  haproxy can proxy to backends on non-standard ports — SELinux blocks this
  by default on Rocky/RHEL. Set `haproxy_selinux_connect_any: false` to skip.


License
-------

GPL-3.0-or-later
