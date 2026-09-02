docker_swarm
============

Initializes and manages a Docker Swarm cluster: node preparation (container
runtime + Docker SDK for Python), swarm init on the first manager, manager
and worker join, and post-join node role/availability/label management.

Uses `community.docker.docker_swarm` / `docker_node` / `docker_swarm_info`
rather than shelling out to the `docker` CLI — these modules are natively
idempotent (`docker_swarm` re-run with unchanged options is a no-op), so
unlike `mgcdrd.infrasvc.k8s`'s `kubeadm` calls there's no manual
stat-a-marker-file gate needed before init.

Tested on: Debian 12/13, Rocky Linux 9/10


Requirements
------------

`become: true` and `gather_facts: true` are required.

The inventory **must** define `docker_swarm_managers` and
`docker_swarm_workers` groups.

Collections:
- `community.docker` (swarm/node management — needs Docker SDK for Python
  on the target, installed by this role's `config` phase)
- `ansible.posix` (firewalld, RedHat only)
- `mgcdrd.infrabase` (`docker` — engine install)


Role Variables
--------------

### Required (no defaults)

| Variable | Description |
|---|---|
| `docker_swarm_init_manager` | `inventory_hostname` of the node that runs the initial swarm init. All other managers and workers join after it. |

### Optional

| Variable | Default | Description |
|---|---|---|
| `docker_swarm_run` | `config` | Phase to execute. See **Phases** below. |
| `docker_swarm_advertise_addr` | `{{ ansible_default_ipv4.address }}` | Address this node advertises to other nodes. |
| `docker_swarm_listen_addr` | `0.0.0.0:2377` | Address/port for inter-manager communication. |
| `docker_swarm_default_addr_pool` | `[]` | Overlay network address pool (CIDR list). Empty uses Docker's default. Init-only. |
| `docker_swarm_subnet_size` | `24` | Default address pool subnet mask length. Init-only. |
| `docker_swarm_firewalld_ports` | see defaults | Ports opened via firewalld on RedHat nodes. |
| `docker_swarm_keepalived_enabled` | `false` | Stop/start keepalived on non-init managers around the join, so the VIP stays pinned to the init manager. |
| `docker_swarm_node_config` | `[]` | List of node role/availability/label changes. See **Node Configuration** below. |


Phases (`docker_swarm_run`)
----------------------------

| Value | What runs | Target |
|---|---|---|
| `config` | Installs `mgcdrd.infrabase.docker`, the Docker SDK for Python (`python3-docker`, via EPEL on RedHat), and opens firewalld ports | All nodes |
| `init` | Initializes the swarm on `docker_swarm_init_manager`, then all nodes join | All nodes |
| `addnodes` | Joins nodes to an already-initialized swarm | New nodes |
| `nodeconfig` | Applies `docker_swarm_node_config` entries | Runs on `docker_swarm_init_manager` only |

Run phases in order: `config` → `init`. Use `addnodes` later when adding new
nodes, and `nodeconfig` to change an existing node's role/availability/labels.


Node Configuration
-------------------

```yaml
docker_swarm_node_config:
  - hostname: worker3.example.com
    availability: drain
  - hostname: worker1.example.com
    labels:
      tier: frontend
```

| Field | Required | Description |
|---|---|---|
| `hostname` | yes | Hostname or ID of the node as registered in swarm. |
| `role` | no | `manager` or `worker`. Omit to leave unchanged. |
| `availability` | no | `active`, `pause`, or `drain`. Omit to leave unchanged. |
| `labels` | no | Dict of node labels. |
| `labels_state` | no | `merge` (default) or `replace`. |

Runs against `docker_swarm_init_manager`'s local Docker socket — no
`delegate_to` needed for the targeted node itself, `docker_node` addresses
it by `hostname` against the swarm API.


Inventory Structure
--------------------

```yaml
all:
  children:
    docker_swarm:
      children:
        docker_swarm_managers:
          hosts:
            swarm-mgr1.example.com:
            swarm-mgr2.example.com:
            swarm-mgr3.example.com:
        docker_swarm_workers:
          hosts:
            swarm-node1.example.com:
            swarm-node2.example.com:
```


Example Playbook
----------------

```yaml
- name: docker_swarm - Node preparation
  hosts: docker_swarm
  become: true
  tags: [config]
  vars:
    docker_swarm_run: config
  roles:
    - mgcdrd.infrasvc.docker_swarm

- name: docker_swarm - Keepalived on managers
  hosts: docker_swarm_managers
  become: true
  tags: [config]
  roles:
    - mgcdrd.infrasvc.keepalived
  vars:
    keepalived_vip_for:
      - dockerswarm

- name: docker_swarm - Cluster initialization
  hosts: docker_swarm
  become: true
  tags: [init, never]
  vars:
    docker_swarm_run: init
    docker_swarm_init_manager: swarm-mgr1.example.com
    docker_swarm_keepalived_enabled: true
  roles:
    - mgcdrd.infrasvc.docker_swarm

- name: docker_swarm - Add nodes
  hosts: docker_swarm
  become: true
  tags: [addnodes, never]
  vars:
    docker_swarm_run: addnodes
    docker_swarm_init_manager: swarm-mgr1.example.com
    docker_swarm_keepalived_enabled: true
  roles:
    - mgcdrd.infrasvc.docker_swarm
```

```bash
ansible-playbook site.yml                        # node prep + keepalived
ansible-playbook site.yml --tags init,addnodes   # initialize swarm and join all nodes
ansible-playbook site.yml --tags addnodes        # join new nodes to existing swarm
```

The `never` tag prevents `init` and `addnodes` from running accidentally on
a plain `ansible-playbook site.yml` invocation — same convention as
`mgcdrd.infrasvc.k8s`.


Companion Roles
----------------

- `mgcdrd.infrasvc.keepalived` — floats a VIP across manager nodes. Set
  `keepalived_vip_for: [dockerswarm]` on the `docker_swarm_managers` group.
- `mgcdrd.infrasvc.docker_swarm_secrets` — pushes Vault-sourced secrets and
  configs into the running swarm.
- `mgcdrd.infrasvc.docker_deploy` — deploys stacks (`docker stack deploy`)
  or standalone Compose projects onto swarm/individual nodes.


License
-------

GPL-3.0-or-later
