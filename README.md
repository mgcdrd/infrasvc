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
| `k8s` | Deploys and configures Kubernetes nodes (master and worker), including OIDC and PSA |
| `keepalived` | Installs and configures keepalived for VRRP/HA |
| `keycloak` | Deploys Keycloak via Docker Compose with TLS, PostgreSQL backend, and optional host/bridge network mode |
| `keycloak_config` | Configures Keycloak post-deploy via REST API: LDAP federation, realms, k8s OIDC client, RBAC |
| `nginx` | Installs and configures Nginx as a web/proxy server |
| `pdns_phpipam` | Deploys PowerDNS (Auth + Recursor + DNSDist) and phpIPAM via Docker Compose |
| `vsftp` | Installs and configures vsftpd |

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