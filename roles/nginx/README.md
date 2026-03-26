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
  - name: mysite               # → /etc/nginx/conf.d/mysite.conf
    server_names:
      - mysite.example.com
    exclude_proxy_files: false
    proxy_files_path: /etc/nginx/conf.d/mysite.proxies
```

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
- **`default_443`**: The catch-all 443 block requires `redir_302_uri` — there is
  no default to avoid accidentally redirecting traffic.
- **`old_shared/`**: Templates in `templates/old_shared/` are superseded by
  `templates/shared_configs/*.j2` and can be removed once the new shared configs
  are confirmed working.
- **keepalived integration**: Pairs with `mgcdrd.infrasvc.keepalived` using the
  `webproxy` preset, which deploys a check script that monitors the nginx process.


License
-------

GPL-3.0-or-later
