vsftp
=====

Installs and configures vsftpd. Generates a fully-managed `/etc/vsftpd.conf`
from Ansible variables, covering all vsftpd options. Every parameter has a
sensible default (matching vsftpd's own defaults); override only what you need.

Tested on: Debian 12/13, Rocky Linux 9/10


Requirements
------------

`become: true` and `gather_facts: true` are required — package installation
and config file writes need root privileges; OS-family detection drives the
SELinux tasks. `community.general` and `ansible.posix` collections must be
installed for the SELinux tasks (both are in `ansible-base-ee`).


Role Variables
--------------

All variables are prefixed `vsftp_` and map 1-to-1 to vsftpd.conf directives.
The full set with descriptions is in `vars/main.yml`. The most commonly
overridden variables are listed below.

### Template output control

```yaml
vsftp_show_comments: false   # include inline comments in generated vsftpd.conf
```

### General

```yaml
vsftp_background: "NO"       # NO = let systemd manage the process (recommended)
vsftp_listen: "YES"          # standalone mode (mutually exclusive with listen_ipv6)
vsftp_listen_ipv6: "NO"
vsftp_listen_port: 21
```

### Local users

```yaml
vsftp_local_enable: "YES"    # allow /etc/passwd users to log in
vsftp_write_enable: "YES"    # allow write commands (STOR, DELE, MKD, etc.)
vsftp_chroot_local_user: "YES"
vsftp_local_umask: "022"
```

### Passive mode

```yaml
vsftp_pasv_enable: "YES"
vsftp_pasv_address: ""       # IP or hostname advertised in PASV response
vsftp_pasv_addr_resolve: "NO"
vsftp_pasv_min_port: 50000
vsftp_pasv_max_port: 50010
```

### SSL/TLS

```yaml
vsftp_ssl_enable: "NO"
vsftp_rsa_cert_file: "/etc/ssl/certs/vsftpd.pem"
vsftp_rsa_private_key_file: ""
vsftp_force_local_logins_ssl: "YES"
vsftp_force_local_data_ssl: "YES"
```

### Logging

```yaml
vsftp_xferlog_enable: "YES"
vsftp_xferlog_std_format: "NO"
vsftp_log_ftp_protocol: "NO"
```

See `vars/main.yml` for the complete list of supported parameters with
descriptions and vsftpd defaults.

### SELinux (RedHat only)

```yaml
vsftp_selinux_register_pasv_ports: true    # register pasv_min_port..pasv_max_port as ftp_port_t
vsftp_selinux_ftpd_full_access:    false   # broader access for non-standard local_root paths
```

Registering the passive port range only happens when `vsftp_pasv_enable` is
truthy and both port bounds are set — SELinux otherwise blocks vsftpd from
binding a non-default passive range even though vsftpd.conf permits it.


Example Playbook
----------------

```yaml
- name: Deploy FTP server
  hosts: ftp_servers
  gather_facts: true
  become: true
  roles:
    - mgcdrd.infrasvc.vsftp
  vars:
    vsftp_listen: "YES"
    vsftp_local_enable: "YES"
    vsftp_write_enable: "YES"
    vsftp_chroot_local_user: "YES"
    vsftp_pasv_enable: "YES"
    vsftp_pasv_address: "ftp.example.com"
    vsftp_pasv_addr_resolve: "YES"
    vsftp_pasv_min_port: 50000
    vsftp_pasv_max_port: 50010
    vsftp_xferlog_enable: "YES"
    vsftp_ssl_enable: "YES"
    vsftp_rsa_cert_file: "/etc/ssl/certs/ftp.example.com.crt"
    vsftp_rsa_private_key_file: "/etc/ssl/private/ftp.example.com.key"
```


Notes
-----

- `vsftp_listen` and `vsftp_listen_ipv6` are mutually exclusive — enable only one.
- `vsftp_background` should be `NO` when vsftpd is managed by systemd (the
  default here). Setting it to `YES` will conflict with systemd's process tracking.
- `vsftp_write_enable` must be `YES` for anonymous upload settings to take effect.
- The role uses `state: latest` for package installation to pick up security patches.
  Switch to `state: present` if you need pinned versions.
- Verified 2026-07-10: the template renders cleanly with zero variable overrides
  (role defaults only) — a prior bug left `vsftp_listen_address6` and
  `vsftp_connect_from_port_20` unwired (a leftover `CHANGEME` placeholder meant
  those two directives silently ignored whatever you set) and `userlist_log`
  referenced `vsftp_userlist_enable` with no `default()`, crashing the template
  entirely unless that one variable was set explicitly. All fixed.


License
-------

GPL-3.0-or-later
