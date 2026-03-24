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

Optionally integrates with a `ssl_scripting` role for self-signed cert
generation. Set `nginx_ssl_enable: true` and populate `nginx_ssl_scripting`
if you need that. For production certs use the `mgcdrd.infrabase.acme_sh` role
independently and point the cert paths at the issued certificates.


Role Variables
--------------

All variables are prefixed `nginx_`. The full annotated structure is in
`vars/main.yml`. Commonly used variables:

### Process

```yaml
nginx_process_user: nginx
nginx_worker_processes: auto
nginx_pid_file: /run/nginx.pid
nginx_load_dynamic_mods: false
```

### Events

```yaml
nginx_events:
  conns: 1024
```

### HTTP block

```yaml
nginx_http_block:
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

These variables are consumed by the templates in `shared_configs/`:

```yaml
nginx_shared_configs:
  ssl:
    ssl_protos:    "TLSv1.2 TLSv1.3"
    ssl_ciphers:   "ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
    ssl_cert_path: /etc/nginx/ssl/server.crt
    ssl_key_path:  /etc/nginx/ssl/server.key
    ssl_dhparam:   /etc/nginx/ssl/dhparam.pem
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


Example Playbook
----------------

```yaml
- name: Deploy nginx reverse proxy
  hosts: proxy_servers
  gather_facts: true
  become: true
  roles:
    - mgcdrd.infrasvc.nginx
  vars:
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
        ssl_cert_path: /etc/ssl/certs/proxy.example.com.crt
        ssl_key_path:  /etc/ssl/private/proxy.example.com.key
        redir_302_uri: https://example.com

    nginx_shared_configs:
      ssl:
        ssl_protos:    "TLSv1.2 TLSv1.3"
        ssl_ciphers:   "ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384"
        ssl_cert_path: /etc/ssl/certs/proxy.example.com.crt
        ssl_key_path:  /etc/ssl/private/proxy.example.com.key
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

- **Shared configs**: `ssl.conf.j2`, `proxy_configs.conf.j2`, `logging.conf.j2`,
  and `useragent.conf.j2` are deployed to `/etc/nginx/conf.d/shared_configs/` and
  included by each server block template via `include .../shared_configs/*.conf`.
- **`block_badagents`**: The `$blockedagent` map must be defined in the `http`
  block (nginx.conf) before it can be used in server blocks. Set
  `nginx_http_block.block_badagents: true` to emit the map, then include
  `useragent.conf` in each server block that should enforce it.
- **`default_443`**: The catch-all 443 block requires `redir_302_uri` to be
  set — there is no default to avoid accidentally redirecting traffic to an
  unintended destination.
- **`old_shared/`**: The templates in `templates/old_shared/` are superseded by
  `templates/shared_configs/*.j2` and can be removed once you have confirmed the
  new shared configs work in your environment.
- **keepalived integration**: This role pairs with `mgcdrd.infrasvc.keepalived`
  using the `webproxy` preset, which deploys a check script that monitors the
  nginx process.


License
-------

GPL-3.0-or-later
