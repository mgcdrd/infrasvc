# k8s

Provisions a Kubernetes cluster across Debian and Rocky Linux nodes. Handles node preparation (swap, sysctl, kernel modules, NetworkManager, CRI-O/kubeadm repos), control plane initialization, Calico CNI deployment, and worker/additional-master joins.

## Requirements

Collections:
- `ansible.posix`
- `community.general`
- `mgcdrd.infrabase` (uses the `etc_hosts` role for `/etc/hosts` management)

## Role Variables

### Required (no defaults)

| Variable | Description |
|----------|-------------|
| `k8s_init_master` | FQDN of the node that runs `kubeadm init`. All other masters join after it. |
| `k8s_control_plane_endpoint` | DNS name for the HA API endpoint (VIP). Used in kubeadm config and cert SANs. |
| `k8s_init_token` | Bootstrap token. Generate with: `printf '%s.%s\n' "$(tr -dc a-z0-9 </dev/urandom \| head -c 6)" "$(tr -dc a-f0-9 </dev/urandom \| head -c 16)"`. Store in vault. |

### Optional (defaults in `defaults/main.yml`)

| Variable | Default | Description |
|----------|---------|-------------|
| `k8s_run` | `config` | Phase: `config`, `init`, or `addnodes` |
| `k8s_version` | `1.32` | Kubernetes and CRI-O version |
| `k8s_calico_version` | `3.31.0` | Calico CNI version |
| `k8s_svc_cidr` | `10.96.0.0/12` | Kubernetes service CIDR |
| `k8s_pod_cidr` | `10.112.0.0/12` | Pod network CIDR |
| `k8s_modules` | `[br_netfilter, overlay]` | Kernel modules loaded on all nodes |
| `k8s_sysctl` | standard k8s params | sysctl parameters written to `/etc/sysctl.d/kubernetes.conf` |
| `k8s_selinux_state` | `Permissive` | SELinux state (RedHat only) |

## Phases (`k8s_run`)

| Value | What runs | Target hosts |
|-------|-----------|--------------|
| `config` | Swap disable, NetworkManager, `/etc/hosts`, kernel modules, sysctl, repos, package install | All nodes |
| `init` | `kubeadm init` on `k8s_init_master`, Calico deploy, then all nodes join | All nodes |
| `addnodes` | Join nodes to an already-initialized cluster | All nodes not yet joined |

## Inventory Structure

```ini
[k8smasters]
k8s-cp1.example.com
k8s-cp2.example.com
k8s-cp3.example.com

[k8sworkers]
k8s-node1.example.com
k8s-node2.example.com

[k8s_nodes:children]
k8smasters
k8sworkers
```

## Example Playbook

```yaml
# Phase 1 — prepare all nodes
- name: k8s node preparation
  hosts: k8s_nodes
  become: true
  roles:
    - mgcdrd.infrasvc.k8s
  vars:
    k8s_run: config

# Phase 2 — initialize and join
- name: k8s cluster init and join
  hosts: k8s_nodes
  become: true
  roles:
    - mgcdrd.infrasvc.k8s
  vars:
    k8s_run:                    init
    k8s_init_master:            k8s-cp1.example.com
    k8s_control_plane_endpoint: k8s-api.example.com
    k8s_init_token:             "{{ vault_k8s_init_token }}"
```

## Companion Roles

- **keepalived** (`keepalived_vip_for: [kubernetes]`) — floats a VIP across control plane nodes using `check_apiserver.sh`.

## Platforms

| OS | Version |
|----|---------|
| Debian | 12 (bookworm), 13 (trixie) |
| Rocky Linux | 9, 10 |
