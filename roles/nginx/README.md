nginx
=====

Installs and configures nginx. Manages `/etc/nginx/nginx.conf`, per-site server
block configs under `/etc/nginx/conf.d/`, and a set of shared config snippets
(SSL hardening, proxy headers, logging, user-agent blocking) deployed to
`/etc/nginx/conf.d/shared_configs/`.

Tested on: Debian 12/13, Rocky Linux 9/10


Requirements
------------

`become: true` and `gather_facts: true` are required.

For SSL cert management, install the appropriate infrabase collection role:

- `ansible-galaxy collection install mgcdrd.infrabase` for both `ssl_scripting`
  and `acme_sh`.


Role Variables
--------------

All variables are prefixed `nginx_`. The full annotated structure is in
`vars/main.yml`. Commonly used variables:

### Process

```yaml
nginx_process_user:      nginx
nginx_worker_processes:  auto
nginx_pid_file:          /run/nginx.pid
nginx_load_dynamic_mods: false
```

### Events

```yaml
nginx_events:
  conns: 1024
```

### HTTP block

`log_formats` must be a **dict**, not a list:

```yaml
nginx_http_block:
  log_formats:
    main: |
      '$remote_addr - $remote_user [$time_local] "$request" '
      '$status $body_bytes_sent "$http_referer" "$http_user_agent"'
    reverse_proxy: |
      '$remote_addr - $remote_user [$time_local] "$request" $status '
      'host="$host" upstream="$upstream_addr" request_time=$request_time'
  log_lines:
    - type:   access_log
      file:   /var/log/nginx/access.log
      format: main
  add_mime: true
  force_80_redirect: true     # global HTTP→HTTPS redirect server block
  hsts_max_age: 63072000
  block_badagents: false      # map-based user-agent blocking in http context
  gzip_comp_lvl: 6
  gzip_buffers: "4 8k"
  client_body_buffer_size: 1k
  client_header_buffer_size: 8k
  large_client_header_buffers: "4 8k"
  add_opts:
    sendfile:    on
    tcp_nopush:  on
    server_tokens: off
  caching:
    enabled:    true
    cache_path: /var/cache/nginx
    keys_zone:  "STATIC:10m"
    inactive:   24h
    max_size:   10g
  default_443:                # catch-all 443 block for unmatched SNI
    enabled: true
    ssl_cert_path: /etc/nginx/ssl/ssl-dummy.crt
    ssl_key_path:  /etc/nginx/ssl/ssl-dummy.key
    redir_302_uri: https://example.com
```

### Shared config snippets

These variables are consumed by the templates in `shared_configs/`. Each
section is optional — if omitted the corresponding config file renders empty.

```yaml
nginx_shared_configs:
  ssl:
    ssl_protos:    "TLSv1.2 TLSv1.3"
    ssl_ciphers:   "ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
    ssl_cert_path: /etc/nginx/ssl/server.crt
    ssl_key_path:  /etc/nginx/ssl/server.key
    ssl_dhparam:   /etc/nginx/ssl/dhparam.pem   # optional; omit to skip directive
  logging:
    - type:   access_log
      path:   /var/log/nginx/shared_access.log
      format: main
```

### Server blocks

One `.conf` file is created per entry:

```yaml
nginx_server_blocks:
  - name: mysite               # → /etc/nginx/conf.d/mysite.conf — a config
                                # filename label only, no SSL/cert significance
    server_names:
      - mysite.example.com
    exclude_proxy_files: false
    proxy_files_path: /etc/nginx/conf.d/proxies/mysite.proxies   # optional — see below
```

**`name` has no relationship to `mgcdrd.infrabase.acme_sh`'s `acme_sh_certs`**
— it's only ever used to name this entry's `.conf` file (and the default
`proxy_files_path`). What actually has to line up is `server_names` here
against `acme_sh_certs[].domains`/`.domain` — a client's SNI hostname (one
of this block's `server_names`) needs a matching cert issued for that
exact domain, via `acme_sh_flat_ssl_dir`'s `<domain>.crt`/`.key` lookup
(see `mgcdrd.infrabase.acme_sh`'s README). The two lists are independent
on purpose — a server block's `name` can be anything, and a single cert's
SANs can cover multiple server blocks — so there's no automatic wiring
between them to get wrong here, only domain names to keep consistent by
hand between the two lists.

### Proxy files (devops-owned location block content)

Deliberate split between infra (this role — the server block shell, certs,
hardening) and whoever owns the actual `proxy_pass`/`location` content per
site: this role only ensures `nginx_proxy_files_dir` and an **empty
placeholder** exist for each `exclude_proxy_files: false` server block —
never the content. `ansible.builtin.copy`'s `force: false` means once a
real file exists there (devops replaced the placeholder), Ansible never
touches it again on any later run.

```yaml
nginx_conf_d_dir: /etc/nginx/conf.d   # optional override — nginx_proxy_files_dir
                                       # (and any custom proxy_files_path) can
                                       # reference this instead of retyping the
                                       # literal path
nginx_proxy_files_dir:   "{{ nginx_conf_d_dir }}/proxies"   # dedicated —
                                                       # deliberately not
                                                       # nginx_conf_d_dir
                                                       # itself, which holds
                                                       # Ansible-managed files
nginx_proxy_files_group: ""   # required whenever any server block has
                               # exclude_proxy_files: false — the group that
                               # owns nginx_proxy_files_dir and every
                               # placeholder in it (the devops service
                               # account that logs in to manage these files
                               # is expected to already exist and belong to
                               # this group — this role does not create it)
```

`nginx_proxy_files_dir` is created `{{ nginx_process_user }}:{{
nginx_proxy_files_group }}`, mode `02770` (setgid, so files the service
account creates inherit the group automatically). Each placeholder file is
the same owner/group, mode `0664`. `proxy_files_path` on a server block
entry still overrides the default `<nginx_proxy_files_dir>/<name>.proxies`
path per site if needed — reference `nginx_conf_d_dir`/`nginx_proxy_files_dir`
there too rather than a hardcoded literal, e.g.
`proxy_files_path: "{{ nginx_proxy_files_dir }}/mysite.proxies"`.

Granting that service account sudo rights to test and reload nginx is done
from the deployment, through `mgcdrd.infrabase.sudoers`'s `sudoers_rules`, not
by this role. With proxy sync (below) nobody edits on the node, so the grant
isn't needed.

### Proxy sync (pull proxy files from S3)

Proxy sync is an opt-in alternative to editing proxy files on a node. The
devops team's CI publishes each site's proxy file to a local S3-compatible
bucket, and a root systemd timer on every node pulls, validates and reloads.
Every node converges on the same content within one interval.

```yaml
nginx_proxy_sync_enabled: true
nginx_proxy_sync_interval: 5min                       # default
nginx_proxy_sync_s3_endpoint: https://s3.example.com:9000   # path-style
nginx_proxy_sync_s3_bucket: proxy
nginx_proxy_sync_s3_prefix: webproxy
# nginx_proxy_sync_s3_region: us-east-1               # default
# nginx_proxy_sync_s3_ca_file: /etc/pki/ca-trust/source/anchors/lab-ca.pem
# nginx_proxy_sync_vault_secret_path defaults to
#   <vault_kv_infra_mount>/data/<vault_kv_env>/webproxy/s3
```

#### Bucket contract

The bucket holds one object per server block with `exclude_proxy_files: false`,
at `<s3_prefix>/<server block name>.proxies`. The role builds that list from
`nginx_server_blocks`, so nothing lists the bucket. The publishing CI job
should run `nginx -t` or a syntax lint before it uploads. The check on the
node is a safety net, not the first line of defense.

#### What each run does

`/usr/local/sbin/nginx-proxy-sync.sh` runs from `nginx-proxy-sync.timer`:

1. It takes a lock, logs in to Vault with AppRole, and reads the S3
   `access_key` and `secret_key` from `nginx_proxy_sync_vault_secret_path`.
   The role_id and secret_id files (`nginx_proxy_sync_vault_*_file`) must
   already be on the node, as with `acme_sh` and `ups_shed`; this role doesn't
   create them. Nothing is cached on disk.
2. It fetches each site's object and compares its sha256 with the installed
   file. A 404 means nothing is published yet, and the current file stays. An
   S3 error or an empty object also keeps the current file and fails the run.
3. If nothing changed, it exits. Otherwise it confirms `nginx -t` passes
   before touching anything, so a pre-existing config problem can't get a good
   file rejected. Then it swaps the changed files in and runs `nginx -t`
   again.
4. If that fails, it restores the old files and retries the changed ones one
   at a time, so one bad site doesn't block the others. A file that fails is
   rolled back and its hash is remembered. The script skips it until the
   published content changes.
5. It runs `nginx -s reload`, never a restart, so a failed reload leaves the
   old workers running. If the reload fails, a `reload-pending` marker makes
   the next run retry it even though no file differs.

The run exits non-zero whenever the node isn't fully in sync: an S3 or Vault
failure, a rejected file, or a failed reload. A failed systemd unit is the
alert. State lives in `nginx_proxy_sync_state_dir`
(`/var/lib/nginx-proxy-sync`).

#### Ownership

With sync enabled, the proxy directory and files are `root:root` (`0755` and
`0644`), and `nginx_proxy_files_group` is no longer required.

#### S3 signing

`nginx-proxy-sync-s3get.py` signs the S3 requests using the host's
`/usr/bin/python3` and only the standard library. It replaces
`curl --aws-sigv4` because Rocky 9's curl 7.76 produced signatures that MinIO
rejected with `SignatureDoesNotMatch`. The host still needs `curl` and `jq`,
which this role installs.

#### Limitations

- Nodes can differ by up to one interval plus 30 seconds of jitter. Per-file
  objects give no atomicity across sites.
- `nginx -t` fails on a `proxy_pass` or `upstream` hostname that doesn't
  resolve, so use IPs or names that resolve.
- `nginx -t` checks syntax. It doesn't catch a valid config that sends
  traffic to the wrong place.
- For a few seconds between swapping a file in and rolling it back, an
  unrelated reload (such as `acme_sh`'s `reload_cmd`) could load the bad file.

### SSL cert management

```yaml
nginx_ssl_enable:   true
nginx_ssl_provider: ""   # ssl_scripting | acme_sh | "" (external/none)
nginx_dhparam_bits: 2048 # bit size for dhparam generation
```

| Provider | Description |
|----------|-------------|
| `ssl_scripting` | Calls `mgcdrd.infrabase.ssl_scripting` to generate self-signed certs and dhparam. Good for internal/testing use. |
| `acme_sh` | Calls `mgcdrd.infrabase.acme_sh` to issue certs via ACME/DNS challenge. For production use. |
| `""` | No cert management — nginx uses whatever certs are already at the configured paths. Run `acme_sh` as a separate play or manage certs externally. |

**ssl_scripting provider** — pass config via `nginx_ssl_scripting`:

```yaml
nginx_ssl_enable:   true
nginx_ssl_provider: ssl_scripting
nginx_ssl_scripting:
  base_dir: /etc/nginx/ssl
  def_bits: 2048
  def_md:   sha256
  country:  US
  state:    XX
  locale:   YY
  org:      Example Corp
  orgunit:  IT
  email:    admin@example.com
```

**acme_sh provider** — set `acme_sh_*` variables directly in your play vars
alongside the `nginx_*` variables (no wrapper needed):

```yaml
nginx_ssl_enable:   true
nginx_ssl_provider: acme_sh

acme_sh_email:    admin@example.com
acme_sh_ca:       letsencrypt
acme_sh_cf_token: "{{ vault_cf_token }}"
acme_sh_certs:
  - domain:    proxy.example.com
    state:     present
    challenge: dns_cf
    reload_cmd: systemctl reload nginx
```

**dhparam**: generated automatically at the path set in
`nginx_shared_configs.ssl.ssl_dhparam` when the provider is `acme_sh` or `""`.
`ssl_scripting` generates its own dhparam — the standalone generation task is
skipped for that provider.


Example Playbook
----------------

```yaml
- name: Deploy nginx reverse proxy (acme_sh certs)
  hosts: proxy_servers
  gather_facts: true
  become: true
  roles:
    - mgcdrd.infrasvc.nginx
  vars:
    nginx_ssl_enable:   true
    nginx_ssl_provider: acme_sh

    acme_sh_email:    admin@example.com
    acme_sh_ca:       letsencrypt
    acme_sh_cf_token: "{{ vault_cf_token }}"
    acme_sh_certs:
      - domain:    proxy.example.com
        state:     present
        challenge: dns_cf
        reload_cmd: systemctl reload nginx

    nginx_http_block:
      add_mime: true
      force_80_redirect: true
      hsts_max_age: 63072000
      block_badagents: true
      add_opts:
        sendfile:      on
        tcp_nopush:    on
        server_tokens: off
      caching:
        enabled:    true
        cache_path: /var/cache/nginx
        keys_zone:  "STATIC:10m"
        inactive:   24h
        max_size:   10g
      default_443:
        enabled:       true
        ssl_cert_path: /etc/nginx/ssl/ssl-dummy.crt
        ssl_key_path:  /etc/nginx/ssl/ssl-dummy.key
        redir_302_uri: https://example.com

    nginx_shared_configs:
      ssl:
        ssl_protos:    "TLSv1.2 TLSv1.3"
        ssl_ciphers:   "ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
        ssl_cert_path: /etc/nginx/ssl/proxy.example.com.crt
        ssl_key_path:  /etc/nginx/ssl/proxy.example.com.key
        ssl_dhparam:   /etc/nginx/ssl/dhparam.pem

    nginx_server_blocks:
      - name: app1
        server_names:
          - app1.example.com
        exclude_proxy_files: false
        proxy_files_path: /etc/nginx/conf.d/app1.proxies
```


Notes
-----

- **`log_formats`**: Must be a YAML dict (not a list of dicts). Each key becomes
  a `log_format` directive name.
- **Shared configs**: `ssl.conf.j2`, `proxy_configs.conf.j2`, `logging.conf.j2`,
  and `useragent.conf.j2` are deployed to `/etc/nginx/conf.d/shared_configs/` and
  included by each server block via `include .../shared_configs/*.conf`. Each
  renders empty if its corresponding `nginx_shared_configs` section is not defined.
- **`block_badagents`**: The `$blockedagent` map must be in the `http` block
  (nginx.conf) before it can be used in server blocks. Set
  `nginx_http_block.block_badagents: true`, then include `useragent.conf` in each
  server block that should enforce it.
- **`exclude_proxy_files`**: Must be set explicitly (`true` or `false`) —
  omitting it entirely behaves like `true` (no proxy include line), since
  the template checks `is defined` first. Every example in this README sets
  it explicitly for that reason; leaving it out silently skips the include
  rather than defaulting to including it, despite the name reading like the
  opposite should be the default.
- **`default_443`**: Fixed 2026-07-10 — `redir_302_uri` having no default meant
  enabling `default_443` without it crashed the whole template render (the
  role failed outright, not just that one block), which defeated the original
  intent of avoiding an accidental redirect by breaking the entire nginx
  config instead. Now falls back to a plain `404` when `redir_302_uri` isn't
  set — same "don't send traffic somewhere unintended" goal, without taking
  the whole render down to enforce it. Set `redir_302_uri` explicitly for
  the original redirect behavior.
- **keepalived integration**: Pairs with `mgcdrd.infrasvc.keepalived` using the
  `webproxy` preset, which deploys a check script that monitors the nginx process.


License
-------

GPL-3.0-or-later
