grafana_alloy
=============

Installs Grafana Alloy from the official Grafana repository and deploys a River
config that handles:

- **Logs → Loki**: tails nginx access and error logs, parses them with regex
  pipeline stages, and forwards to a Loki push endpoint.
- **Metrics → Prometheus**: collects nginx stub_status metrics and optional
  host/system metrics, then remote-writes to a Prometheus-compatible endpoint.

Each section is independently enabled/disabled. Both default to `true`.

Tested on: Debian 12/13, Rocky Linux 9/10


Requirements
------------

`become: true` and `gather_facts: true` are required.

For log forwarding, the `alloy` user must be able to read the nginx log files
(typically requires adding it to the `adm` group or adjusting log permissions).

For metrics, nginx must have `ngx_http_stub_status_module` enabled with a
`/nginx_status` location accessible from localhost.


Role Variables
--------------

All variables are prefixed `grafana_alloy_`.

### Loki (log forwarding)

```yaml
grafana_alloy_loki_enabled: true

grafana_alloy_loki_url:      ""  # required when loki_enabled
grafana_alloy_loki_user:     ""  # optional basic auth
grafana_alloy_loki_password: ""  # use {{ vault_grafana_alloy_loki_password }}

grafana_alloy_nginx_access_log_path: "/var/log/**/*.access.log"
grafana_alloy_nginx_error_log_path:  "/var/log/**/*.error.log"
grafana_alloy_log_sync_period:       "10s"
```

The log processing pipeline is tightly coupled to the nginx log format produced
by `mgcdrd.infrasvc.nginx`. The access log regex expects fields:
`remote_addr`, `remote_user`, `time_local`, `request`, `status`,
`body_bytes_sent`, `http_referer`, `http_user_agent`, `host`, `server`,
`xff`, `upstream`, `request_time`, `upstream_response_time`.

### Prometheus (metrics)

```yaml
grafana_alloy_prometheus_enabled: true

grafana_alloy_remote_write_url:      ""  # required when prometheus_enabled
grafana_alloy_remote_write_user:     ""  # optional basic auth
grafana_alloy_remote_write_password: ""  # use {{ vault_grafana_alloy_remote_write_password }}

# nginx stub_status
grafana_alloy_nginx_stub_status_uri: "http://127.0.0.1/nginx_status"
grafana_alloy_nginx_scrape_interval: "15s"

# Host/system metrics (prometheus.exporter.unix)
grafana_alloy_node_metrics_enabled: true
grafana_alloy_node_scrape_interval: "30s"

# Extra labels applied to all Prometheus metrics
grafana_alloy_extra_labels: {}
# Example:
# grafana_alloy_extra_labels:
#   env: production
#   host_role: proxy
```

### Config path

```yaml
grafana_alloy_config_path: /etc/alloy/config.alloy
```


Example Playbook
----------------

```yaml
- name: Deploy Grafana Alloy on nginx proxy servers
  hosts: proxy_servers
  gather_facts: true
  become: true
  roles:
    - mgcdrd.infrasvc.grafana_alloy
  vars:
    # Loki
    grafana_alloy_loki_url:      "https://loki.example.com/loki/api/v1/push"
    grafana_alloy_loki_user:     "alloy"
    grafana_alloy_loki_password: "{{ vault_grafana_alloy_loki_password }}"

    # Prometheus
    grafana_alloy_remote_write_url:      "https://mimir.example.com/api/v1/push"
    grafana_alloy_remote_write_user:     "alloy"
    grafana_alloy_remote_write_password: "{{ vault_grafana_alloy_remote_write_password }}"

    grafana_alloy_extra_labels:
      env:       production
      host_role: proxy
```


Notes
-----

- **Log file permissions (RedHat)**: When `grafana_alloy_loki_enabled: true`
  on a RedHat host, the role automatically:
  - Sets `/var/log/nginx` to `nginx:nginx 0750` (recursively fixes ownership)
  - Adds the `alloy` user to the `nginx` group (required to traverse the directory)
  - Patches `/etc/logrotate.d/nginx` so rotated files are created as `nginx:nginx`

  On Debian, `/var/log/nginx` is typically `root:adm 0755` and log files are
  `adm`-readable out of the box — no fix needed.
- **Alloy HTTP server**: The built-in UI/debug server listens on
  `0.0.0.0:12345` (set by the package's systemd unit). To change it, set
  `CUSTOM_ARGS=--server.http.listen-addr=<addr>` in `/etc/default/alloy`
  (Debian) or `/etc/sysconfig/alloy` (RedHat).
- **nginx stub_status**: A minimal location block:

  ```nginx
  location /nginx_status {
      stub_status;
      allow 127.0.0.1;
      deny  all;
  }
  ```

- **Grafana repository**: Adds `https://apt.grafana.com` (Debian) or
  `https://rpm.grafana.com` (RedHat) and installs the `alloy` package.
  The latest stable release is always installed.


License
-------

GPL-3.0-or-later
