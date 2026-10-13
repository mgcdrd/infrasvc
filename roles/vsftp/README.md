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

### Variable reference

The Default column shows vsftpd's own built-in default, which is what the template renders when the variable is unset. Every `vsftp_*` variable maps 1-to-1 to a `vsftpd.conf` directive; the role-only settings are `vsftp_show_comments`, `vsftp_show_defaults`, and `vsftp_selinux_*`.

| Variable | Default | Required | Description |
|---|---|---|---|
| `vsftp_show_comments` | `false` | No | Include inline comments in the generated `/etc/vsftpd.conf` |
| `vsftp_background` | `"NO"` | No | `background`: `NO` lets systemd manage the process (normal case), `YES` daemonizes |
| `vsftp_selinux_register_pasv_ports` | `true` | No | RedHat only: register the passive port range as `ftp_port_t` so SELinux lets vsftpd bind it; no-op when PASV is off |
| `vsftp_selinux_ftpd_full_access` | `false` | No | RedHat only: set the `ftpd_full_access` SELinux boolean, needed when home directories sit outside the expected FTP paths |
| `vsftp_show_defaults` | `true` | No | Show directives that are at their default value in the generated file (boolean) |
| `vsftp_rsa_private_key_file` | `(none)` | No | Location of the RSA private key for SSL; if unset the key is expected in the cert file (string) |
| `vsftp_dirlist_enable` | `YES` | No | Allow directory listing commands (boolean) |
| `vsftp_vsftpd_log_file` | `/var/log/vsftpd.log` | No | File for vsftpd-style logs when `xferlog_enable` is set without `xferlog_std_format`, or with `dual_log_enable`; not written when `syslog_enable` is set (string) |
| `vsftp_listen` | `NO` | No | If YES, vsftpd will run in standalone mode. must not be run from inetd mutually exclusive from listen_ipv6 (boolean) |
| `vsftp_listen_ipv6` | `NO` | No | Listen on IPv6 not v4 mutually exclusive from 'listen' (boolean) |
| `vsftp_delete_failed_uploads` | `NO` | No | If YES, any failed upload file is deleted (boolean) |
| `vsftp_one_process_model` | `NO` | No | Don't enable unless you know what you are doing (boolean) |
| `vsftp_reverse_lookup_enable` | `NO` | No | Use hostname over IP before pam auth (when pam_access setup for it) (boolean) |
| `vsftp_run_as_launching_user` | `NO` | No | Run vsftpd as user which launched it DO NOT EVER ENABLE - see man page (boolean) |
| `vsftp_session_support` | `NO` | No | Controls is vsftpd attempts to maintain sessions for logins. only works if pam auth, and uses utmp and wtmp - performance hit (boolean) |
| `vsftp_setproctitle_enable` | `NO` | No | If YES, session status in system process listing leave off for security (boolean) |
| `vsftp_use_sendfile` | `NO` | No | Internal setting used for testing the benefits of using the sendfile() system call (boolean) |
| `vsftp_nopriv_user` | `NO` | No | User vsftpd use when wants to be totally unpriv should be dedicated user, not nobody (string) |
| `vsftp_pam_service_name` | `NO` | No | Name of PAM service vsftp will use (string) |
| `vsftp_mdtm_write` | `NO` | No | Allow MDTM to set file mod times (boolean) |
| `vsftp_secure_chroot_dir` | `NO` | No | Used for secure chroot at time vsftpd does req FS access should be empty and not be writable by ftp user (string) |
| `vsftp_delay_successful_login` | `NO` | No | Num of sec to pause prior to allowing a successful login (integer) |
| `vsftp_port_enable` | `NO` | No | If NO, disallow PORT method of obtaining data conn (boolean) |
| `vsftp_port_promiscuous` | `NO` | No | If YES, disable PORT security check ensuring outgoing conn only conn to client (boolean) |
| `vsftp_pasv_enable` | `NO` | No | Server tell client IP and port for data xfer....leave on when proxying (boolean) |
| `vsftp_pasv_addr_resolve` | `NO` | No | If YES, use hostname (not IP) in pasv_address (boolean) |
| `vsftp_pasv_promiscuous` | `NO` | No | If YES, disable PASV sec check ensuring data conn origin same IP as control conn LEAVE AS NO! (boolean) |
| `vsftp_listen_address` | `NO` | No | If in standalone mode, listen address (string) |
| `vsftp_listen_address6` | `NO` | No | If in standalone mode, listen address format is standard IPv6 address (string) |
| `vsftp_listen_port` | `NO` | No | If in standalone mode, port to listen for connections (integer) |
| `vsftp_data_connection_timeout` | `NO` | No | Timeout in sec for stalled xfers (integer) |
| `vsftp_idle_session_timeout` | `NO` | No | Timeout in sec between FTP command (integer) |
| `vsftp_max_login_fails` | `NO` | No | Max login attempts before kicked (integer) |
| `vsftp_max_clients` | `NO` | No | Max num of clients, excess get error message '0' is unlimited (integer) |
| `vsftp_max_per_ip` | `NO` | No | Max num clients from same IP '0' is unlimited (integer) |
| `vsftp_isolate_network` | `NO` | No | If YES, use CLONE_NEWNET to isolate untrusted proccessees so can't arbitrary connect() and have to ask the privileged proccess for sockets 'port_promiscuous'… (boolean) |
| `vsftp_isolate` | `NO` | No | If YES, use CLONE_NEWPID and CLONE_NEWIPC to isolate processes to their ipc and pid namespaces searapated processes cannot interface with each other (boolean) |
| `vsftp_trans_chunk_size` | `NO` | No | Amt of data to send in each packet '0' vsftpd picks 'sensible' (integer) |
| `vsftp_tcp_wrappers` | `NO` | No | Allows for tcp_wrappers control - keep off (boolean) |
| `vsftp_connect_from_port_20` | `NO` | No | Controls PORT style data connections use port 20 (ftp-data) (boolean) |
| `vsftp_ftp_data_port` | `NO` | No | If connect_from_port_20 YES, port for PORT style conns originate (integer) |
| `vsftp_connect_timeout` | `NO` | No | Timeout in secs for remote client to respond to PORT style data connection (integer) |
| `vsftp_pasv_address` | `NO` | No | Override IP address vsftpd will advertise in response to PASV cmd. specify IP unless 'pasv_addr_resolve' is enabled then can be hostname (string) |
| `vsftp_pasv_min_port` | `NO` | No | Lowest port for PASV style data conns (integer) |
| `vsftp_pasv_max_port` | `NO` | No | Highest port for PASV style data conns (integer) |
| `vsftp_accept_timeout` | `NO` | No | Timeout in sec for a remote client to establish connection with a PASV style data connection (integer) |
| `vsftp_ssl_enable` | `NO` | No | Enable support for SSL conns on control (login) and data client needs SSL support too - suggest to keep off (boolean) |
| `vsftp_ssl_request_cert` | `NO` | No | Request, not require, SSL cert on incoming conns (boolean) |
| `vsftp_require_ssl_reuse` | `NO` | No | All SSL data conns req SSL session reuse might break some clients (boolean) |
| `vsftp_implicit_ssl` | `NO` | No | Force SSL on all connections (FTPS) (boolean) |
| `vsftp_force_local_data_ssl` | `NO` | No | All non-anon forced to SSL to send and receive data on data connections only if ssl_enable: YES (boolean) |
| `vsftp_force_local_logins_ssl` | `NO` | No | All non-anon forced to SSL to send the password only if ssl_enable: YES (boolean) |
| `vsftp_force_anon_logins_ssl` | `NO` | No | All anon forced to SSL to send the password only if ssl_enable: YES (boolean) |
| `vsftp_force_anon_data_ssl` | `NO` | No | All anon forced to SSL to send and receive data on data connections only if ssl_enable: YES (boolean) |
| `vsftp_require_cert` | `NO` | No | All SSL client conns req'd to present client cert. degree of validation - validate_cert (boolean) |
| `vsftp_validate_cert` | `NO` | No | All SSL client certificates received must validate OK. Self-signed certs do not constitute OK validation (boolean) |
| `vsftp_ssl_sslv2` | `NO` | No | Permit SSLv2 (deprecated).  TLSv1 preferred only if ssl_enable: YES (boolean) |
| `vsftp_ssl_sslv3` | `NO` | No | Permit SSLv3 (deprecated).  TLSv1 preferred (boolean) |
| `vsftp_ssl_tlsv1` | `NO` | No | Permit TLSv1 (boolean) |
| `vsftp_strict_ssl_read_eof` | `NO` | No | SSL data ULs req term by SSL not an EOF - can break some clients required to prevent premature termination with TCP FIN (boolean) |
| `vsftp_strict_ssl_write_shutdown` | `NO` | No | SSL data DLs req term by SSL not an EOF (boolean) |
| `vsftp_ca_certs_file` | `NO` | No | Location of CA certs from for validating client (string) |
| `vsftp_rsa_cert_file` | `NO` | No | Location of RSA certs for SSL encryption (string) |
| `vsftp_dsa_cert_file` | `NO` | No | Location of DSA cert for SSL encryption default (none - an RSA certificate suffices) (string) |
| `vsftp_dsa_private_key_file` | `NO` | No | Location of DSA private key for SSL encryption. priv key expected in same file as cert defaiult: (none) (string) |
| `vsftp_ssl_ciphers` | `NO` | No | SSL ciphers allowed by vsftpd. see ciphers man page. (string) |
| `vsftp_debug_ssl` | `NO` | No | OpenSSL conn diag dumped into vsftpd log (boolean) |
| `vsftp_ftpd_banner` | `NO` | No | Sting options allows override greeting banner when conn first comes in (string) |
| `vsftp_banner_file` | `NO` | No | File containing text to display when conn'ing overrides banner provided by 'ftpd_banner' (string) |
| `vsftp_ascii_download_enable` | `NO` | No | ASCII mode data xfers honored for DLs (boolean) |
| `vsftp_ascii_upload_enable` | `NO` | No | ASCII mode data xfers honored for ULs (boolean) |
| `vsftp_dirmessage_enable` | `NO` | No | Users shown message when entering new dir. by default, scans for .message file in current/new directory (boolean) |
| `vsftp_force_dot_files` | `NO` | No | Show all listing without need for '-a' (boolean) |
| `vsftp_ls_recurse_enable` | `NO` | No | Allow recurvise listing with 'ls -R' (boolean) |
| `vsftp_text_userdb_names` | `NO` | No | 'ls' shows user and group name slows performance (boolean) |
| `vsftp_tilde_user_enable` | `NO` | No | Tilde paths will try to be resolve ~user only resolve if /etc/passwd within _current_ chroot jail (boolean) |
| `vsftp_file_open_mode` | `NO` | No | Perms of UL files umask applied to this value (string) |
| `vsftp_lock_upload_files` | `NO` | No | ULs proceed with write lock; DLs w/ shared read lock. WARN can be used to starve writer (boolean) |
| `vsftp_deny_file` | `NO` | No | Pattern of files/dirs should NOT be accessible at all File system perms better option... (string) |
| `vsftp_hide_file` | `NO` | No | Pattern for files/dir should be hidden still accessible unless in deny_file (string) |
| `vsftp_use_localtime` | `NO` | No | Display dir in local time zone - also affects MDTM FTP cmd (boolean) |
| `vsftp_message_file` | `NO` | No | If dirmessage_enable enabled, name of file looked for when dir is entered to be displayed to user (string) |
| `vsftp_hide_ids` | `NO` | No | Show user and grp as 'ftp' (boolean) |
| `vsftp_user_config_dir` | `NO` | No | Set to a dir, when user logs in, vsftpd looks in dir for username named file for settings to apply can't be affected 'listen_address', 'banner_file',… (string) |
| `vsftp_write_enable` | `NO` | No | Write cmds enabled STOR, DELE, RNFR, RNTO, MKD, RMD, APPE and SITE (boolean) |
| `vsftp_download_enable` | `NO` | No | Allow DLs (boolean) |
| `vsftp_cmds_allowed` | `NO` | No | Allowed FTP cmds post login USER, PASS and QUIT and others are always allowed pre-login (string) |
| `vsftp_cmds_denied` | `NO` | No | List of denies FTP cmds deny takes precedence (string) |
| `vsftp_async_abor_enable` | `NO` | No | Enable FTP cmd 'async ABOR' ill advised clients will use; awkward to handle some clients will hang on cancelled xfer unless enabled (boolean) |
| `vsftp_anonymous_enable` | `NO` | No | If enabled, both the usernames 'ftp' and 'anonymous' are recognised as anonymous logins (boolean) |
| `vsftp_allow_anon_ssl` | `NO` | No | Allow anon user to use SSL conns only if ssl_enable: YES (boolean) |
| `vsftp_secure_email_list_enable` | `NO` | No | Specified list of e-mail passwords for anonymous logins to be accepted (boolean) |
| `vsftp_email_password_file` | `NO` | No | Alternate file for 'secure_email_list_enable' setting (string) |
| `vsftp_deny_email_enable` | `NO` | No | Deny list of emails file /etc/vsftpd/banned_emails or specified with banned_email_file (boolean) |
| `vsftp_banned_email_file` | `NO` | No | If deny_email_enable enabled, file path of anon emails not permitted (string) |
| `vsftp_no_anon_password` | `NO` | No | Vsftpd doesn't ask anon password; straight login (boolean) |
| `vsftp_anon_root` | `NO` | No | Dir to drop anon users to failure is silently ignored (string) |
| `vsftp_ftp_username` | `NO` | No | User used for handling anon FTP. home dir is root dir of anon FTP area (string) |
| `vsftp_check_shell` | `NO` | No | Check /etc/shells for valid user shell for local logins only affects non-PAM builds of vsftpd (boolean) |
| `vsftp_anon_max_rate` | `NO` | No | Max data xfer rate in bytes/sec for anon clients (integer) |
| `vsftp_anon_upload_enable` | `NO` | No | Allow anon to UL - required for virt users to UL only if write_enable: YES and ftp user has write perms to parent (boolean) |
| `vsftp_chown_uploads` | `NO` | No | All anon ULs will be chownd to 'chown_username' (boolean) |
| `vsftp_chown_username` | `NO` | No | If chown_uploads set, user who is given ownership of anon UL files (string) |
| `vsftp_anon_umask` | `NO` | No | Umask for anon user file creation (prefix with 0 for octal) (integer) |
| `vsftp_chown_upload_mode` | `NO` | No | File mode to force for chowned anon ULs default" 0600 (integer) |
| `vsftp_anon_mkdir_write_enable` | `NO` | No | Allow anon to create new dirs only if write_enable: YES and ftp user has write perms to parent (boolean) |
| `vsftp_anon_other_write_enable` | `NO` | No | Allow anon user to delete and rename (boolean) |
| `vsftp_anon_world_readable_only` | `NO` | No | Anon user only allowed to DL files which are world read (boolean) |
| `vsftp_local_enable` | `NO` | No | Allow normal users in /etc/passwd (or PAM) to login must be enabled to non-anon login to work (boolean) |
| `vsftp_userlist_enable` | `NO` | No | If YES, users in 'userlist_file' denied (boolean) |
| `vsftp_userlist_deny` | `NO` | No | If userlist_enable YES and this is NO, users denied unless in userlist_file (boolean) |
| `vsftp_userlist_file` | `NO` | No | If userlist_enable enabled, file path containing names dfault: /etc/vsftpd/user_list (string) |
| `vsftp_chroot_list_enable` | `NO` | No | Chown local users specified in /etc/vsftpd/chroot_list or 'chroot_list_file' if chroot_local_user is YES, reverses and doesn't chroot given users (boolean) |
| `vsftp_chroot_local_user` | `NO` | No | Place local users in chroot jail into home dir security implications.....if users have shell or upload perms. use with caution (boolean) |
| `vsftp_chroot_list_file` | `NO` | No | If chroot_list_enable enabled, file with list of local users which will be chroot'd in their home dirs if chroot_local_user enabled, becomes users NOT in chroot (string) |
| `vsftp_passwd_chroot_enable` | `NO` | No | Works with chroot_local_user user jails derive from home dir string in /etc/passwd (boolean) |
| `vsftp_chmod_enable` | `NO` | No | For local users, anon never can (boolean) |
| `vsftp_local_max_rate` | `NO` | No | Max xfer in bytes/sec for local auth users (integer) |
| `vsftp_local_umask` | `NO` | No | Umask for local user file creation (prefix with 0 for octal) (integer) |
| `vsftp_local_root` | `NO` | No | Dir to put local users into.  fails silently (string) |
| `vsftp_guest_enable` | `NO` | No | All non-anon classed as 'guest' and remapped to user in guest_username (boolean) |
| `vsftp_guest_username` | `NO` | No | Username of guest user mapped to. (string) |
| `vsftp_virtual_use_local_privs` | `NO` | No | Virtual users have same privileges as local users default v users same as anon (boolean) |
| `vsftp_user_sub_token` | `NO` | No | Useful for virt users - gen home dir for virt user. if set to'$USER' and home dir of real user specified via guest_username is /home/virtual/$USER (string) |
| `vsftp_dual_log_enable` | `NO` | No | Log to /var/log/xferlog and /var/log/vsftpd.log former is a wu-ftpd style transfer log, parseable by standard tools latter is vsftpd's own style log. (boolean) |
| `vsftp_xferlog_enable` | `NO` | No | Logs maintained for UL and DL. normally /var/log/vsftpd.log, change with vsftpd_log_file (boolean) |
| `vsftp_xferlog_std_format` | `NO` | No | Transfer log file in standard xferlog format (like wu-ftpd). useful for xfer stat generators, default format more readable. log file set by xferlog_file (boolean) |
| `vsftp_xferlog_file` | `NO` | No | If (dual_log_enable set) OR (if xferlog_enable and xferlog_std_format is set), file to write wu-ftpd style transfer (string) |
| `vsftp_log_ftp_protocol` | `NO` | No | All FTP reqs and resp logged; provided xferlog_std_format is not enabled (boolean) |
| `vsftp_syslog_enable` | `NO` | No | Log output for /var/log/vsftpd.log geos to syslog as FTPD facility (boolean) |
| `vsftp_delay_failed_login` | `NO` | No | Num of sec to pause before reporting failed login (integer) |
| `vsftp_userlist_log` | `NO` | No | If userlist_enable is activated, every login denial based on the user list will be logged (boolean) |
| `vsftp_no_log_lock` | `NO` | No | Prevent vsftpd locking log files only use on Solaris and Veritas (boolean) |


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
