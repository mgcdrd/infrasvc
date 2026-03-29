k8s
===

Provisions a Kubernetes cluster across Debian and Rocky Linux nodes. Handles
node preparation (swap, sysctl, kernel modules, NetworkManager, `/etc/hosts`),
container runtime install, Kubernetes repo/package install, control plane
initialization, Calico CNI deployment, and worker/additional-master joins.

Node preparation delegates to `mgcdrd.infrabase` roles:

- `kernel_modules` — loads and persists required kernel modules
- `sysctl` — writes `/etc/sysctl.d/kubernetes.conf`
- `etc_hosts` — writes cluster node entries to `/etc/hosts`
- `crio` / `docker` / `podman` — installs the selected container runtime

Tested on: Debian 12/13, Rocky Linux 9/10


Requirements
------------

`become: true` and `gather_facts: true` are required.

Collections:
- `community.general` (modprobe, lvol)
- `mgcdrd.infrabase`


Role Variables
--------------

### Required (no defaults)

| Variable                    | Description                                                                     |
|-----------------------------|---------------------------------------------------------------------------------|
| `k8s_init_master`           | FQDN of the node that runs `kubeadm init`. All other masters join after it.    |
| `k8s_control_plane_endpoint`| DNS name or VIP for the HA API endpoint. Used in kubeadm config and cert SANs. |
| `k8s_init_token`            | Bootstrap token. See generation command below. Store in Vault — do not commit. |

Generate `k8s_init_token`:
```bash
printf '%s.%s\n' "$(tr -dc a-z0-9 </dev/urandom | head -c 6)" \
                 "$(tr -dc a-f0-9 </dev/urandom | head -c 16)"
```

### Optional

| Variable                | Default          | Description                                                              |
|-------------------------|------------------|--------------------------------------------------------------------------|
| `k8s_run`               | `config`         | Phase to execute. See **Phases** below.                                  |
| `k8s_version`           | `1.32`           | Kubernetes minor version. Also passed to the container runtime role.     |
| `k8s_calico_version`    | `3.31.0`         | Calico CNI version.                                                      |
| `k8s_container_runtime` | `cri-o`          | Runtime to install: `cri-o`, `docker`, or `podman`.                     |
| `k8s_svc_cidr`          | `10.96.0.0/12`   | Kubernetes service CIDR.                                                 |
| `k8s_pod_cidr`          | `10.112.0.0/12`  | Pod network CIDR.                                                        |
| `k8s_cluster_group`     | `""`             | Inventory group written to `/etc/hosts`. Auto-detected when empty.       |
| `k8s_modules`           | `[br_netfilter, overlay]` | Kernel modules loaded on all nodes via `infrabase.kernel_modules`. |
| `k8s_sysctl`            | see defaults     | sysctl parameters passed to `infrabase.sysctl`.                         |
| `k8s_selinux_state`     | `Permissive`     | SELinux state on RedHat nodes.                                           |


Phases (`k8s_run`)
------------------

| Value       | What runs                                                                         | Target            |
|-------------|-----------------------------------------------------------------------------------|-------------------|
| `config`    | Swap disable, NetworkManager, `/etc/hosts`, kernel modules, sysctl, container runtime, repos, packages | All nodes |
| `init`      | `kubeadm init` on `k8s_init_master`, Calico deploy, then all nodes join          | All nodes         |
| `addnodes`  | Join nodes to an already-initialized cluster                                      | New nodes         |

Run phases in order: `config` → `init`. Use `addnodes` later when adding new
nodes to an existing cluster.


Container Runtimes
------------------

The runtime is selected via `k8s_container_runtime` and installed by the
corresponding `mgcdrd.infrabase` role.

| Value    | Role                      | CRI-compliant | Notes                                      |
|----------|---------------------------|---------------|--------------------------------------------|
| `cri-o`  | `mgcdrd.infrabase.crio`   | Yes           | Recommended. `crio_version` = `k8s_version`.|
| `docker` | `mgcdrd.infrabase.docker` | No            | Requires `cri-dockerd` shim (not managed). |
| `podman` | `mgcdrd.infrabase.podman` | No            | Requires additional shim (not managed).    |


Inventory Structure
-------------------

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
ansible-playbook site.yml                  # runs config only (safe default)
ansible-playbook site.yml --tags init      # initialize cluster
ansible-playbook site.yml --tags addnodes  # join new nodes
```

The `never` tag prevents `init` and `addnodes` from running accidentally on a
plain `ansible-playbook site.yml` invocation.


Companion Roles
---------------

- `mgcdrd.infrasvc.keepalived` — floats a VIP across control plane nodes using
  `check_apiserver.sh`. Set `keepalived_vip_for: [kubernetes]`.
