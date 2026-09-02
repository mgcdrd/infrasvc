docker_swarm_secrets
=====================

Manages Docker Swarm secrets and configs from a variable list. Generic — it
ships none of its own and isn't tied to any specific deployment, same shape
as `mgcdrd.infrabase.cron_jobs`/`file_deploy`.

Pushes secret/config content into the swarm's encrypted raft store instead
of baking credentials into compose files or environment variables — secrets
are mounted as tmpfs inside service containers at runtime, never written to
a container image or a flat file on disk. `data` values should come from
`{{ vault_<name> }}`, per the collection's secrets convention — never a
hardcoded default.

Tested on: Debian 12/13, Rocky Linux 9/10


Requirements
------------

`become: true` is required. Must run against a Docker Swarm manager node
with the Docker SDK for Python installed — both handled by
`mgcdrd.infrasvc.docker_swarm`'s `config` phase if this role runs against
the same hosts.

Collections:
- `community.docker`


Role Variables
--------------

```yaml
docker_secrets: []
# docker_secrets:
#   - name: keycloak_db_password
#     data: "{{ vault_keycloak_db_password }}"
#   - name: old_api_key
#     state: absent

docker_configs: []
# docker_configs:
#   - name: haproxy_cfg
#     data: "{{ lookup('template', 'haproxy.cfg.j2') }}"
```

| Field | Required | Description |
|---|---|---|
| `name` | yes | Secret/config name — used as the idempotency key. |
| `data` | yes, unless `state: absent` | The value. Source secrets from `{{ vault_<name> }}`. |
| `labels` | no | Dict of metadata labels. |
| `force` | no | `true` always removes and recreates, even if unchanged. Default: `false` — the module tracks a content hash automatically, so normal rotation (changing `data`) updates in place without it. |
| `state` | no | `present` (default) or `absent`. |


Rotation
--------

Updating a secret's `data` and re-running the role removes the old secret
and creates a new one under the same name — Docker secrets are immutable
once created. Services referencing the secret by name need a
`docker service update --force` (or a stack redeploy) to pick up the new
version; this role does not do that automatically, same caveat as
`mgcdrd.infrabase.docker`'s log-driver note about existing containers.


Example Playbook
----------------

```yaml
- name: Push secrets into the swarm
  hosts: docker_swarm_managers[0]
  become: true
  roles:
    - mgcdrd.infrasvc.docker_swarm_secrets
  vars:
    docker_secrets:
      - name: keycloak_db_password
        data: "{{ vault_keycloak_db_password }}"
```


Dependencies
------------

No role dependencies. Requires a swarm manager target and the
`community.docker` collection.


License
-------

GPL-3.0-or-later
