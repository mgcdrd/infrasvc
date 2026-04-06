k8s
===

Provisions a Kubernetes cluster across Debian and Rocky Linux nodes. Handles
node preparation (swap, sysctl, kernel modules, NetworkManager, `/etc/hosts`),
container runtime install, Kubernetes repo/package install, control plane
initialization with Calico CNI, worker/additional-master joins, keepalived
for HA VIP, and helm + Python kubernetes library on masters for platform
bootstrap.

Node preparation delegates to `mgcdrd.infrabase` roles:

- `kernel_modules` — loads and persists required kernel modules
- `sysctl` — writes `/etc/sysctl.d/kubernetes.conf`
- `etc_hosts` — writes cluster node entries to `/etc/hosts`
- `crio` / `docker` / `podman` — installs the selected container runtime

Tested on: Debian 12/13, Rocky Linux 9/10


Requirements
------------

`become: true` and `gather_facts: true` are required.

The inventory **must** define a `k8smasters` group. The helm and Python
kubernetes library install tasks use `groups['k8smasters']` to limit
execution to control plane nodes.

Collections:
- `community.general` (modprobe, lvol)
- `mgcdrd.infrabase`


Role Variables
--------------

### Required (no defaults)

| Variable                     | Description                                                                      |
|------------------------------|----------------------------------------------------------------------------------|
| `k8s_init_master`            | FQDN of the node that runs `kubeadm init`. All other masters join after it.     |
| `k8s_control_plane_endpoint` | DNS name or VIP for the HA API endpoint. Used in kubeadm config and cert SANs.  |
| `k8s_init_token`             | Bootstrap token. See generation command below. Store in Vault — do not commit.  |

Generate `k8s_init_token`:
```bash
printf '%s.%s\n' "$(tr -dc a-z0-9 </dev/urandom | head -c 6)" \
                 "$(tr -dc a-f0-9 </dev/urandom | head -c 16)"
```

### Optional

| Variable                | Default                    | Description                                                               |
|-------------------------|----------------------------|---------------------------------------------------------------------------|
| `k8s_run`               | `config`                   | Phase to execute. See **Phases** below.                                   |
| `k8s_version`           | `1.32`                     | Kubernetes minor version. Also passed to the container runtime role.      |
| `k8s_calico_version`    | `3.31.0`                   | Calico CNI version.                                                       |
| `k8s_container_runtime` | `cri-o`                    | Runtime to install: `cri-o`, `docker`, or `podman`.                      |
| `k8s_svc_cidr`          | `10.96.0.0/12`             | Kubernetes service CIDR.                                                  |
| `k8s_pod_cidr`          | `10.112.0.0/12`            | Pod network CIDR.                                                         |
| `k8s_cluster_group`     | `""`                       | Inventory group written to `/etc/hosts`. Auto-detected when empty.        |
| `k8s_helm_version`      | `4`                        | Helm major version to install on masters (`3` or `4`).                   |
| `k8s_modules`           | `[br_netfilter, overlay]`  | Kernel modules loaded on all nodes via `infrabase.kernel_modules`.        |
| `k8s_sysctl`            | see defaults               | sysctl parameters passed to `infrabase.sysctl`.                          |
| `k8s_selinux_state`     | `Permissive`               | SELinux state on RedHat nodes.                                            |


Phases (`k8s_run`)
------------------

| Value      | What runs                                                                                                   | Target    |
|------------|-------------------------------------------------------------------------------------------------------------|-----------|
| `config`   | Swap disable, NetworkManager, `/etc/hosts`, kernel modules, sysctl, container runtime, repos, packages, helm + python3-kubernetes on masters | All nodes |
| `init`     | `kubeadm init` on `k8s_init_master`, Calico CNI deploy, then all nodes join                                | All nodes |
| `addnodes` | Join nodes to an already-initialized cluster                                                                | New nodes |

Run phases in order: `config` → `init`. Use `addnodes` later when adding new
nodes to an existing cluster.


Container Runtimes
------------------

| Value    | Role                      | CRI-compliant | Notes                                       |
|----------|---------------------------|---------------|---------------------------------------------|
| `cri-o`  | `mgcdrd.infrabase.crio`   | Yes           | Recommended. `crio_version` = `k8s_version`.|
| `docker` | `mgcdrd.infrabase.docker` | No            | Requires `cri-dockerd` shim (not managed).  |
| `podman` | `mgcdrd.infrabase.podman` | No            | Requires additional shim (not managed).     |


Helm on Masters
---------------

During the `config` phase, masters receive:
- **helm** — installed via the official `get-helm-<version>.sh` script.
  Version is controlled by `k8s_helm_version` (default: `4`).
- **python3-kubernetes** — required by `kubernetes.core` Ansible modules.

These are prerequisites for the `k8s-platform` deployment
(`deployments/k8s-platform`), which runs platform bootstrap (MetalLB,
cert-manager, NFS, Vault) directly on the init master rather than copying
the kubeconfig to the management host.


Inventory Structure
-------------------

The `k8smasters` and `k8sworkers` groups must be children of `k8s`:

```yaml
all:
  children:
    k8s:
      children:
        k8smasters:
          hosts:
            k8s-cp1.example.com:
            k8s-cp2.example.com:
            k8s-cp3.example.com:
        k8sworkers:
          hosts:
            k8s-node1.example.com:
            k8s-node2.example.com:
```


Example Playbook
----------------

Using the recommended `site.yml` structure with tags to control phases:

```yaml
- name: k8s - Node preparation
  hosts: k8s
  become: true
  tags: [config]
  vars:
    k8s_run: config
  roles:
    - mgcdrd.infrasvc.k8s

- name: k8s - Extend /var filesystem
  hosts: k8s
  become: true
  tags: [config]
  vars:
    lvm_volumes:
      - lv:       lv_var
        size:     256G
        resizefs: true
        mount:    /var
  roles:
    - mgcdrd.infrabase.lvm2

- name: k8s - Keepalived on masters
  hosts: k8smasters
  become: true
  tags: [config]
  roles:
    - mgcdrd.infrasvc.keepalived

- name: k8s - Cluster initialization
  hosts: k8s
  become: true
  tags: [init, never]
  vars:
    k8s_run: init
  roles:
    - mgcdrd.infrasvc.k8s

- name: k8s - Add nodes
  hosts: k8s
  become: true
  tags: [addnodes, never]
  vars:
    k8s_run: addnodes
  roles:
    - mgcdrd.infrasvc.k8s
```

```bash
ansible-playbook site.yml                        # node prep + LVM + keepalived
ansible-playbook site.yml --tags init,addnodes   # initialize cluster and join all nodes
ansible-playbook site.yml --tags addnodes        # join new nodes to existing cluster
```

The `never` tag prevents `init` and `addnodes` from running accidentally on a
plain `ansible-playbook site.yml` invocation.


OIDC Authentication
-------------------

The role can configure the API server to accept JWT tokens from an external
OIDC provider (e.g. Keycloak). Set `k8s_oidc_enabled: true` and supply the
remaining variables before running the `init` phase — these flags are baked
into the kubeadm `InitConfiguration` and cannot be changed without restarting
the API server or re-running kubeadm.

| Variable | Default | Description |
|---|---|---|
| `k8s_oidc_enabled` | `false` | Enable OIDC API server flags |
| `k8s_oidc_issuer_url` | `""` | OIDC issuer URL (e.g. `https://infra-kc.example.com/realms/lab`) |
| `k8s_oidc_client_id` | `kubernetes` | OIDC client ID |
| `k8s_oidc_username_claim` | `preferred_username` | JWT claim used as the k8s username |
| `k8s_oidc_groups_claim` | `groups` | JWT claim used for group membership |

The Keycloak side is configured by `mgcdrd.infrasvc.keycloak_config`, which
creates the `kubernetes` OIDC client with the matching claims mappers. After
both roles run, create `ClusterRoleBindings` in the k8s-platform deployment to
map OIDC groups to k8s ClusterRoles.

Example (`deployments/k8s/inventory/group_vars/k8s/main.yml`):

```yaml
k8s_oidc_enabled:    true
k8s_oidc_issuer_url: "https://infra-kc.example.com/realms/lab"
k8s_oidc_client_id:  "kubernetes"
```


Companion Roles
---------------

- `mgcdrd.infrasvc.keepalived` — floats a VIP across control plane nodes.
  Set `keepalived_vip_for: [kubernetes]` on the `k8smasters` group.
- `mgcdrd.infrabase.lvm2` — extends logical volumes. Used in the deployment
  to grow `/var` after swap removal frees space in the VG.


Companion Deployments
---------------------

- `deployments/k8s` — the deployment that uses this role. Manages inventory,
  group vars, and the three-phase site.yml.
- `deployments/k8s-platform` — day-2 platform bootstrap (MetalLB, cert-manager,
  NFS provisioner, Vault). Runs on the init master using the kubeconfig left by
  kubeadm — no kubeconfig copy to the management host required.
