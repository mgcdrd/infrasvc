# Ansible Collection - mgcdrd.infrasvc

## Overview

This collection contains common infrastructure roles used to standardize and automate:

- HAProxy TCP support
- Kubernetes
- keepalived
- Nginx
- vsftpd

## Roles

| Role | Description |
|------|-------------|
| `haproxy` | Installs and configures HAProxy (TCP mode) |
| `k8s` | Deploys and configures Kubernetes nodes (master and worker) |
| `keepalived` | Installs and configures keepalived for VRRP/HA |
| `nginx` | Installs and configures Nginx as a web/proxy server |
| `vsftp` | Installs and configures vsftpd |
| `pdns_phpipam` | Deploys PowerDNS (Auth + Recursor + DNSDist) and phpIPAM via Docker Compose |

It is designed for use with:
- Ansible Core >= 2.14
- AWX / Automation Controller
- Execution Environments

---

## Installation

### From Git (recommended for internal use)

Add to `collections/requirements.yml`:

```yaml
collections:
  - name: mgcdrd.infrasvc
    source: https://GITLAB_URL/ansible/collections/infrasvc.git
    type: git
    version: v0.2.0