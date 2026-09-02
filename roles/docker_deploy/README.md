docker_deploy
=============

Deploys Docker workloads from a variable list, dispatching per-entry onto
either `docker stack deploy` (swarm) or `docker compose up` (a single
non-swarm node). Generic — it ships no deployments of its own and isn't
tied to any specific service, same shape as
`mgcdrd.infrabase.cron_jobs`/`file_deploy`.

Both `community.docker.docker_stack` and `docker_compose_v2` shell out to
the `docker`/`docker compose` CLI rather than the Docker API — no Docker
SDK for Python dependency, unlike `mgcdrd.infrasvc.docker_swarm`/
`docker_swarm_secrets`.

Tested on: Debian 12/13, Rocky Linux 9/10


Requirements
------------

`become: true` is required. `mgcdrd.infrabase.docker` must already be
installed on the target — this role does not install it.

Collections:
- `community.docker`


Role Variables
--------------

```yaml
docker_deploy: []
# docker_deploy:
#   - name: monitoring
#     mode: stack
#     compose:
#       - /opt/stacks/monitoring/compose.yml
#     prune: true
#   - name: pihole
#     mode: compose
#     project_src: /opt/compose/pihole
```

| Field | Required | Applies to | Description |
|---|---|---|---|
| `name` | yes | both | Stack/project name — used as the idempotency key. |
| `mode` | no | both | `stack` or `compose`. Default: `compose`. |
| `compose` | yes for `stack` | stack | List of compose file paths on the target host, or inline compose dicts. |
| `project_src` | yes for `compose` | compose | Path to a directory containing a compose file on the target host. |
| `files` | no | compose | Compose file names relative to `project_src`, instead of the default `compose.yml`. |
| `prune` | no | stack | Remove services no longer in the stack definition. Default: `false`. |
| `with_registry_auth` | no | stack | Send registry auth details to swarm agents. Default: `false`. |
| `resolve_image` | no | stack | `always`, `changed`, or `never`. |
| `state` | no | both | `present` (default) or `absent`. |

Fields are passed straight through to the underlying module's own option
names (`docker_stack` for `mode: stack`, `docker_compose_v2` for
`mode: compose`) — see those modules' docs for the full option set beyond
what's listed here.


Mode Selection
--------------

- **`stack`** — targets a swarm manager. Use for services that should run
  as swarm services (replicated, placement constraints, rolling updates).
  Requires `mgcdrd.infrasvc.docker_swarm` to have already initialized the
  swarm on the target.
- **`compose`** — targets any individual Docker host, swarm or not. Use for
  simple single-node workloads that don't need swarm scheduling.


Example Playbook
----------------

```yaml
- name: Deploy stacks to the swarm
  hosts: docker_swarm_managers[0]
  become: true
  roles:
    - mgcdrd.infrasvc.docker_deploy
  vars:
    docker_deploy:
      - name: monitoring
        mode: stack
        compose:
          - /opt/stacks/monitoring/compose.yml
        prune: true

- name: Deploy standalone compose project
  hosts: pihole1.example.com
  become: true
  roles:
    - mgcdrd.infrasvc.docker_deploy
  vars:
    docker_deploy:
      - name: pihole
        mode: compose
        project_src: /opt/compose/pihole
```


Dependencies
------------

No role dependencies. Requires `community.docker` and a working Docker
engine on the target (`mgcdrd.infrabase.docker`).


License
-------

GPL-3.0-or-later
