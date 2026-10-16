Master Variables List for infrasvc
===================================


docker_deploy Role Variables
--------------

Deploys Docker workloads from a variable list, dispatching per-entry onto
either `docker stack deploy` (swarm) or `docker compose up` (a single
non-swarm node). Generic — it ships no deployments of its own and isn't
tied to any specific service, same shape as
`mgcdrd.infrabase.cron_jobs`/`file_deploy`.

Both `community.docker.docker_stack` and `docker_compose_v2` shell out to
the `docker`/`docker compose` CLI rather than the Docker API — no Docker
SDK for Python dependency, unlike `mgcdrd.infrasvc.docker_swarm`/
`docker_swarm_secrets`.

[`mgcdrd.infrasvc.docker_deploy`](roles/docker_deploy/README.md)

**General role variables**

| Name          | Default | Required | Purpose |
|---------------|---------|----------|---------|
| docker_deploy | `[]`    | Yes      | Stacks (swarm) or standalone Compose projects to deploy (fields below); empty is a no-op |


**docker_deploy[] variables**

| Field              | Required          | Applies to | Description |
|--------------------|-------------------|------------|-------------|
| name               | Yes               | both       | Stack/project name — used as the idempotency key. |
| mode               | No                | both       | `stack` or `compose`. Default: `compose`. |
| compose            | Yes for `stack`   | stack      | List of compose file paths on the target host, or inline compose dicts. |
| project_src        | Yes for `compose` | compose    | Path to a directory containing a compose file on the target host. |
| files              | No                | compose    | Compose file names relative to `project_src`, instead of the default `compose.yml`. |
| prune              | No                | stack      | Remove services no longer in the stack definition. Default: `false`. |
| with_registry_auth | No                | stack      | Send registry auth details to swarm agents. Default: `false`. |
| resolve_image      | No                | stack      | `always`, `changed`, or `never`. |
| state              | No                | both       | `present` (default) or `absent`. |


docker_swarm Role Variables
--------------

Initializes and manages a Docker Swarm cluster: node preparation (container
runtime + Docker SDK for Python), swarm init on the first manager, manager
and worker join, and post-join node role/availability/label management.

Uses `community.docker.docker_swarm` / `docker_node` / `docker_swarm_info`
rather than shelling out to the `docker` CLI — these modules are natively
idempotent (`docker_swarm` re-run with unchanged options is a no-op), so
unlike `mgcdrd.infrasvc.k8s`'s `kubeadm` calls there's no manual
stat-a-marker-file gate needed before init.

[`mgcdrd.infrasvc.docker_swarm`](roles/docker_swarm/README.md)

**General role variables**

| Variable                        | Default                  | Required | Description |
|---------------------------------|--------------------------|----------|-------------|
| docker_swarm_run                | `config`                 | No       | Phase to run: `config` (node prep), `init` (init swarm and join all nodes), `addnodes` (join to an existing swarm), `nodeconfig` (role/availability/label changes) |
| docker_swarm_advertise_addr     | *(primary IPv4 address)* | No       | Address the init manager advertises to other nodes |
| docker_swarm_listen_addr        | `"0.0.0.0:2377"`         | No       | Address and port for inter-manager communication |
| docker_swarm_default_addr_pool  | `[]`                     | No       | Overlay network address pool, used only at init; empty keeps Docker's built-in default (10.0.0.0/8 in /24s) |
| docker_swarm_subnet_size        | `24`                     | No       | Subnet mask length carved from the default address pool; init only |
| docker_swarm_firewalld_ports    | *(list, 4 items)*        | Yes      | Swarm ports opened on every node (RedHat only): 2377/tcp, 7946/tcp+udp, 4789/udp |
| docker_swarm_keepalived_enabled | `false`                  | No       | During `addnodes`, stop keepalived on non-init managers while they join so the VIP stays on the init manager |
| docker_swarm_node_config        | `[]`                     | If `docker_swarm_run: nodeconfig` | Node role/availability/label changes; each item maps to `community.docker.docker_node` and needs `hostname` |
| docker_swarm_init_manager       | `""`                     | Yes      | `inventory_hostname` of the node that runs the initial swarm init; all other managers and workers join after it |

**docker_swarm_node_config[] variables**

| Field        | Required | Description |
|--------------|----------|-------------|
| hostname     | Yes      | Hostname or ID of the node as registered in swarm. |
| role         | No       | `manager` or `worker`. Omit to leave unchanged. |
| availability | No       | `active`, `pause`, or `drain`. Omit to leave unchanged. |
| labels       | No       | Dict of node labels. |
| labels_state | No       | `merge` (default) or `replace`. |


docker_swarm_secrets Role Variables
--------------

Manages Docker Swarm secrets and configs from a variable list. Generic — it
ships none of its own and isn't tied to any specific deployment, same shape
as `mgcdrd.infrabase.cron_jobs`/`file_deploy`.

Pushes content into the swarm's encrypted raft store instead of baking
credentials into compose files or environment variables; secrets are
mounted as tmpfs inside service containers at runtime. Must run against a
swarm manager with the Docker SDK for Python (handled by
`mgcdrd.infrasvc.docker_swarm`'s `config` phase).

[`mgcdrd.infrasvc.docker_swarm_secrets`](roles/docker_swarm_secrets/README.md)

**General role variables**

| Variable       | Default | Required | Description |
|----------------|---------|----------|-------------|
| docker_secrets | `[]`    | No       | Swarm secrets to manage, sourced from Vault (fields below) |
| docker_configs | `[]`    | No       | Swarm configs to manage (fields below) |

**docker_secrets[] and docker_configs[] variables**

| Field  | Required                    | Description |
|--------|-----------------------------|-------------|
| name   | Yes                         | Secret/config name — used as the idempotency key. |
| data   | Yes, unless `state: absent` | The value. Source secrets from `{{ vault_<name> }}`. |
| labels | No                          | Dict of metadata labels. |
| force  | No                          | `true` always removes and recreates, even if unchanged. Default: `false` — the module tracks a content hash automatically, so normal rotation (changing `data`) updates in place without it. |
| state  | No                          | `present` (default) or `absent`. |


foreman_config Role Variables
--------------

Configures a running Foreman + Katello instance with the `theforeman.foreman`
collection: content (sync plans, GPG keys, products, repositories, lifecycle
environments, content views, activation keys), infrastructure (domains,
subnets, realms, architectures, compute resources/profiles), provisioning
(operating systems, partition tables, installation media, global
parameters), template sync from GitLab, host groups, LDAP auth sources,
user groups, AWX integration, and SCAP content/tailoring files/policies.

Fully data-driven — every list is optional and its tasks are skipped when
undefined. Each area has its own tag so it can be re-run alone.

[`mgcdrd.infrasvc.foreman_config`](roles/foreman_config/README.md)

**General role variables**

| Variable                                    | Default                            | Required                         | Description |
|---------------------------------------------|------------------------------------|----------------------------------|-------------|
| foreman_hostname                            | `"{{ ansible_fqdn }}"`             | No                               | Foreman server FQDN |
| foreman_url                                 | `"https://{{ foreman_hostname }}"` | No                               | Foreman API base URL |
| foreman_org                                 | `"My Organization"`                | No                               | Organization the content is created under |
| foreman_location                            | `"Default Location"`               | No                               | Location the content is created under |
| foreman_validate_certs                      | `true`                             | No                               | Validate the Foreman API TLS certificate |
| foreman_username                            | *(unset)*                          | Yes                              | Foreman API user |
| vault_foreman_admin_password                | *(unset)*                          | Yes                              | Foreman API password |
| foreman_sync_plans                          | *(unset)*                          | No                               | Sync plans |
| foreman_gpg_keys                            | `[]`                               | No                               | GPG content credentials, read from the role's `files/`; referenced by `foreman_repos_rpm[].gpg_key` |
| foreman_repo_products                       | *(unset)*                          | No                               | Products |
| foreman_repos_rpm                           | `[]`                               | No                               | Yum repositories |
| foreman_repos_deb                           | `[]`                               | No                               | Deb repositories |
| foreman_lifecycle_envs                      | `[]`                               | No                               | Lifecycle environments |
| foreman_content_views                       | `[]`                               | No                               | Content views; `first_publish: true` publishes and promotes v1.0 once |
| foreman_activation_keys                     | `[]`                               | No                               | Activation keys |
| foreman_domains                             | `[]`                               | No                               | Domains |
| foreman_subnets                             | `[]`                               | No                               | Subnets and their smart proxies |
| foreman_realms                              | `[]`                               | No                               | Realms |
| foreman_architectures                       | `[]`                               | No                               | Architectures |
| foreman_compute_resources                   | `[]`                               | No                               | Compute resources (e.g. Proxmox); passwords from `{{ vault_<name> }}` |
| foreman_compute_profiles                    | `[]`                               | No                               | Compute profiles |
| foreman_operatingsystems_rh                 | `[]`                               | No                               | RedHat-family OSes, with partition tables, media, and template map |
| foreman_operatingsystems_deb                | `[]`                               | No                               | Debian OSes, same shape plus `release_name` |
| foreman_partition_table_os_families         | `[]`                               | No                               | Partition table to OS family mapping |
| foreman_installation_media                  | `[]`                               | No                               | Installation media |
| foreman_global_parameters                   | `[]`                               | No                               | Global parameters; `hidden: true` for secrets |
| foreman_template_gitlab_host                | *(unset)*                          | If template sync                 | GitLab host scanned into the `foreman` user's `known_hosts` |
| foreman_template_repo                       | *(unset)*                          | If template sync                 | Git URL templates are imported from |
| foreman_template_import_associate           | `always`                           | No                               | Template import `associate` |
| foreman_template_import_branch              | `main`                             | No                               | Branch imported from |
| foreman_template_import_dirname             | `/`                                | No                               | Directory within the repo |
| foreman_template_import_filter              | *(omitted)*                        | No                               | Regex limiting which templates are imported |
| foreman_template_import_force               | `false`                            | No                               | Overwrite locked templates |
| foreman_template_settings                   | `[]`                               | No                               | Foreman settings (`name`, `value`) applied before the sync |
| vault_foreman_template_sync_ssh_private_key | *(unset)*                          | If template sync                 | Persistent ed25519 key for the `foreman` user; the public half is registered on GitLab once |
| vault_foreman_template_sync_ssh_public_key  | *(unset)*                          | If template sync                 | Public half of that key |
| foreman_hostgroups                          | *(unset)*                          | No                               | Host groups |
| vault_foreman_host_root_pass                | *(unset)*                          | If a host group sets `root_pass` | Root password for provisioned hosts |
| foreman_ldap_auth_sources                   | *(unset)*                          | No                               | Plain LDAP auth sources, for sites without IPA |
| foreman_usergroups                          | *(unset)*                          | No                               | User groups mapped to external (IPA) or LDAP groups |
| foreman_awx_url                             | *(unset)*                          | No                               | AWX URL; AWX tasks are skipped when undefined |
| foreman_awx_job_template_id                 | `""`                               | If `foreman_awx_url`             | AWX job template ID for provisioning callbacks |
| foreman_awx_provider                        | `awx`                              | No                               | Ansible provider type |
| foreman_awx_inventory_enabled               | `true`                             | No                               | Register Foreman as an AWX inventory source |
| vault_awx_host_config_key                   | `""`                               | If `foreman_awx_url`             | AWX host config key |
| foreman_scap_contents                       | `[]`                               | No                               | Extra SCAP datastreams (`scap-security-guide` content is seeded automatically) |
| foreman_scap_tailoring_files                | `[]`                               | No                               | SCAP tailoring files |
| foreman_scap_policies                       | `[]`                               | No                               | Compliance policies; content, profile, and host groups referenced by name |


Note: See [`mgcdrd.infrasvc.foreman_config README.md`](roles/foreman_config/README.md) for the fields of each list and the tags


foreman_host_network Role Variables
--------------

Updates an existing Foreman host's interface — subnet, IP, and optionally
VLAN tag — via `theforeman.foreman.host`. Matches the interface by
`identifier` when set, otherwise by `name` (a managed primary interface is
named after the host FQDN).

The VLAN tag only reaches the hypervisor if the host is
compute-resource-linked in Foreman. Hosts cloned directly against the
Proxmox API only get Foreman's record updated — use
`mgcdrd.proxmox.proxmox_nic` for the real change.

[`mgcdrd.infrasvc.foreman_host_network`](roles/foreman_host_network/README.md)

**General role variables**

| Variable                                  | Default                        | Required | Description |
|-------------------------------------------|--------------------------------|----------|-------------|
| foreman_host_network_url                  | *(lab-specific; see defaults)* | No       | Foreman API base URL |
| foreman_host_network_username             | `""`                           | Yes      | Foreman API user |
| foreman_host_network_password             | `""`                           | Yes      | Foreman API password; use `{{ vault_* }}` |
| foreman_host_network_validate_certs       | `true`                         | No       | Validate the Foreman API TLS certificate |
| foreman_host_network_host                 | `""`                           | Yes      | Foreman host whose interface is updated |
| foreman_host_network_subnet               | `""`                           | Yes      | Target Foreman subnet name |
| foreman_host_network_ip                   | `""`                           | Yes      | New IP for the interface |
| foreman_host_network_interface_identifier | `""`                           | No       | Interface to update (e.g. `ens18`); set for multi-NIC hosts |
| foreman_host_network_vlan_tag             | `""`                           | No       | VLAN tag to set on the interface; see the caveat above |


foreman_install Role Variables
--------------

Installs Foreman 3.x + Katello on Rocky Linux 9 with
`foreman-installer`. Handles the pre-install sequence — Katello client
cleanup, storage preflight, repositories, packages, firewalld, IPA keytab
pre-enrollment, optional custom certificate check — then renders and runs
the installer script from variables. Rocky Linux 9 only.

[`mgcdrd.infrasvc.foreman_install`](roles/foreman_install/README.md)

**General role variables**

| Variable                                     | Default                                           | Required                            | Description |
|----------------------------------------------|---------------------------------------------------|-------------------------------------|-------------|
| foreman_version                              | `"3.19"`                                          | No                                  | Foreman release to install |
| foreman_katello_version                      | `"4.21"`                                          | No                                  | Katello release to install |
| foreman_puppet_release                       | `"openvox8"`                                      | No                                  | Puppet/OpenVox repo release |
| foreman_installer_scenario                   | `katello`                                         | No                                  | `foreman-installer` scenario |
| foreman_skip_storage_check                   | `false`                                           | No                                  | Skip the preflight check that `/var/lib/{pulp,containers,pgsql}` are large enough |
| foreman_storage_min_pulp_gb                  | `290`                                             | No                                  | Minimum available GB on the Pulp mount |
| foreman_storage_min_containers_gb            | `28`                                              | No                                  | Minimum available GB on the containers mount |
| foreman_storage_min_pgsql_gb                 | `18`                                              | No                                  | Minimum available GB on the PostgreSQL mount |
| foreman_hostname                             | `"{{ ansible_fqdn }}"`                            | No                                  | Foreman server FQDN |
| foreman_url                                  | `"https://{{ foreman_hostname }}"`                | No                                  | Foreman base URL |
| foreman_org                                  | `"My Organization"`                               | Yes                                 | Initial organization; set in group_vars |
| foreman_location                             | `"Default Location"`                              | Yes                                 | Initial location; set in group_vars |
| vault_foreman_admin_username                 | *(unset)*                                         | Yes                                 | Initial admin username |
| vault_foreman_admin_password                 | *(unset)*                                         | Yes                                 | Initial admin password |
| vault_foreman_db_password                    | *(unset)*                                         | Yes                                 | Foreman database password |
| foreman_installer_cli_enable                 | *(list, 6 items)*                                 | No                                  | hammer CLI modules enabled (`--enable-foreman-cli-<item>`) |
| foreman_installer_plugin_enable              | *(list, 9 items)*                                 | No                                  | Foreman plugins enabled |
| foreman_installer_proxy_plugin_enable        | *(list, 4 items)*                                 | No                                  | Smart Proxy plugins enabled |
| foreman_installer_further_enable             | *(list, 1 items)*                                 | No                                  | Additional packages enabled (`--enable-<item>`) |
| foreman_dhcp_enable                          | `false`                                           | No                                  | Manage DHCP on the smart proxy |
| foreman_dhcp_provider                        | `isc`                                             | No                                  | DHCP provider |
| foreman_dhcp_interface                       | `eth0`                                            | No                                  | Interface DHCP listens on |
| foreman_dhcp_gateway                         | `""`                                              | If `foreman_dhcp_enable`            | Gateway handed out by DHCP |
| foreman_dhcp_range_start                     | `""`                                              | If `foreman_dhcp_enable`            | First address of the DHCP range |
| foreman_dhcp_range_end                       | `""`                                              | If `foreman_dhcp_enable`            | Last address of the DHCP range |
| foreman_dhcp_nameservers                     | `[]`                                              | No                                  | DNS servers handed out by DHCP |
| foreman_dns_enable                           | `false`                                           | No                                  | Manage DNS on the smart proxy |
| foreman_dns_provider                         | `powerdns`                                        | No                                  | `powerdns` or `nsupdate` |
| foreman_dns_forwarders                       | `[]`                                              | No                                  | DNS forwarders |
| foreman_pdns_api_url                         | `"http://localhost:8081"`                         | No                                  | PowerDNS API URL |
| vault_pdns_api_key                           | *(unset)*                                         | If `foreman_dns_provider: powerdns` | PowerDNS API key |
| foreman_dns_nsupdate_server                  | `""`                                              | If `foreman_dns_provider: nsupdate` | DNS server that receives nsupdate updates |
| foreman_tftp_enable                          | `true`                                            | No                                  | Manage TFTP on the smart proxy |
| foreman_tftp_listen_on                       | `https`                                           | No                                  | Protocols TFTP serves: `http`, `https`, or `both` |
| foreman_proxy_template_url                   | `""`                                              | No                                  | Smart proxy template URL; empty uses the installer default |
| foreman_realm_enable                         | `false`                                           | No                                  | Enable realm (FreeIPA) integration |
| foreman_realm_pam_server                     | `foreman`                                         | No                                  | PAM service name for realm authentication |
| foreman_realm_ipa_authentication             | `"true"`                                          | No                                  | Enable IPA authentication (installer string boolean) |
| foreman_realm_ipa_authentication_api         | `"false"`                                         | No                                  | Enable IPA authentication for the API (installer string boolean) |
| foreman_realm_proxy                          | `"true"`                                          | No                                  | Enable the realm smart-proxy feature (installer string boolean) |
| foreman_realm_provider                       | `freeipa`                                         | No                                  | Realm provider |
| foreman_realm_principal                      | `""`                                              | If `foreman_realm_enable`           | Kerberos principal the realm proxy uses |
| vault_foreman_realm_agent_password           | *(unset)*                                         | If `foreman_realm_enable`           | Password for `foreman_realm_principal`, used for keytab retrieval |
| foreman_realm_freeipa_remove_dns             | `"false"`                                         | No                                  | Remove DNS records when a realm host is deleted (installer string boolean) |
| foreman_ipa_controller                       | `""`                                              | If `foreman_realm_enable`           | IPA server the realm proxy talks to |
| foreman_realm_vault_rotate                   | `false`                                           | No                                  | Reset the realm principal's password after each keytab fetch and write it back to Vault, since `ipa-getkeytab` rotates the key |
| foreman_realm_vault_addr                     | `""`                                              | If `foreman_realm_vault_rotate`     | Vault address holding the realm principal's password |
| foreman_realm_vault_kv_mount                 | `""`                                              | If `foreman_realm_vault_rotate`     | KV mount for the password |
| foreman_realm_vault_path                     | `""`                                              | If `foreman_realm_vault_rotate`     | KV path for the password |
| foreman_realm_vault_password_key             | `"realm_agent_password"`                          | No                                  | Key within the secret holding the password |
| vault_ipa_admin_user                         | *(unset)*                                         | If `foreman_realm_vault_rotate`     | IPA account allowed to change only the realm principal's password |
| vault_ipa_admin_password                     | *(unset)*                                         | If `foreman_realm_vault_rotate`     | Its password |
| foreman_puppet_autosign_entries              | `"[*.example.com]"`                               | No                                  | Puppet autosign patterns |
| foreman_puppetserver_tmpdir                  | `/opt/puppetlabs/server/data/puppetserver/tmp`    | No                                  | JVM temp directory for puppetserver |
| foreman_proxy_content_enable_ansible         | `true`                                            | No                                  | Enable the Ansible Pulp content type |
| foreman_proxy_content_enable_deb             | `true`                                            | No                                  | Enable the deb Pulp content type |
| foreman_proxy_content_enable_docker          | `false`                                           | No                                  | Enable the container Pulp content type |
| foreman_proxy_content_enable_file            | `true`                                            | No                                  | Enable the file Pulp content type |
| foreman_proxy_content_enable_ostree          | `true`                                            | No                                  | Enable the OSTree Pulp content type |
| foreman_proxy_content_enable_python          | `true`                                            | No                                  | Enable the Python Pulp content type |
| foreman_proxy_content_enable_yum             | `true`                                            | No                                  | Enable the yum Pulp content type |
| foreman_proxy_content_pulpcore_mirror        | `false`                                           | No                                  | Mirror pulpcore content on the proxy |
| foreman_proxy_openscap_ansible_module        | `true`                                            | No                                  | Install the OpenSCAP Ansible module on the proxy |
| foreman_proxy_rex_script_enabled             | `true`                                            | No                                  | Enable remote execution (script provider) |
| foreman_proxy_rex_script_cockpit_integration | `false`                                           | No                                  | Enable the Cockpit integration for remote execution |
| foreman_plugin_tasks_automatic_cleanup       | `true`                                            | No                                  | Clean up old tasks automatically |
| foreman_plugin_tasks_backup                  | `true`                                            | No                                  | Back up tasks before cleanup |
| foreman_certs_city                           | `Raleigh`                                         | No                                  | City for the internal certificates |
| foreman_certs_country                        | `US`                                              | No                                  | Country for the internal certificates |
| foreman_certs_org                            | `"My Organization"`                               | No                                  | Organization for the internal certificates |
| foreman_certs_org_unit                       | `IT`                                              | No                                  | Organizational unit for the internal certificates |
| foreman_certs_state                          | `NC`                                              | No                                  | State for the internal certificates |
| foreman_custom_certs                         | `false`                                           | No                                  | Replace the self-signed web certificate with the files below |
| foreman_cert_path                            | `"/etc/ssl/acme/{{ foreman_hostname }}/cert.pem"` | If `foreman_custom_certs`           | Web certificate path |
| foreman_cert_key_path                        | `"/etc/ssl/acme/{{ foreman_hostname }}/key.pem"`  | If `foreman_custom_certs`           | Web certificate key path |
| foreman_cert_ca_path                         | `"/etc/ssl/acme/{{ foreman_hostname }}/ca.pem"`   | If `foreman_custom_certs`           | CA chain path |
| foreman_telemetry_logger_enabled             | `false`                                           | No                                  | Enable the logger telemetry sink |
| foreman_telemetry_prometheus_enabled         | `false`                                           | No                                  | Enable the Prometheus telemetry endpoint |
| foreman_telemetry_statsd_enabled             | `false`                                           | No                                  | Enable the statsd telemetry sink |


google_publicca_eab Role Variables
--------------

Mints a Google Cloud Public CA external account binding (EAB) key on
demand via `gcloud publicca external-account-keys create`, and writes the
result to HashiCorp Vault so an ACME client (e.g.
[`mgcdrd.infrabase.acme_sh`](../../../infrabase/roles/acme_sh)) can
register or recover an ACME account with Google's Public CA.

This role only calls the GCP API and Vault — it never touches a managed
host's OS, so it runs entirely against the control node (`delegate_to:
localhost` internally). Include it in a play targeting the real
consuming host so `google_publicca_eab_account_name` defaults to a
meaningful value; the role itself does nothing on that host.


[`mgcdrd.infrasvc.google_publicca_eab`](roles/google_publicca_eab/README.md)

**General role variables**

| Variable                                 | Default                      | Required | Description |
|------------------------------------------|------------------------------|----------|-------------|
| google_publicca_eab_project              | `""`                         | Yes      | GCP project ID that owns the Public CA external account key |
| google_publicca_eab_vault_gcp_token_path | `""`                         | Yes      | Full Vault path (mount included) that returns a short-lived GCP access token from the GCP secrets engine |
| google_publicca_eab_account_name         | `"{{ inventory_hostname }}"` | No       | Label for the ACME account the key will register |
| google_publicca_eab_vault_addr           | `""`                         | Yes      | Vault address, used for both the GCP token read and the KV write |
| google_publicca_eab_vault_kv_mount       | `""`                         | Yes      | KV mount the minted key is written to |
| google_publicca_eab_vault_path           | `""`                         | Yes      | KV path the minted key is written to |


haproxy Role Variables
--------------

Installs and configures HAProxy. Generates `/etc/haproxy/haproxy.cfg` from
Ansible variables covering all standard HAProxy sections: global, defaults,
mailers, resolvers, frontends, and backends.

Sets `net.ipv4.ip_nonlocal_bind=1` via sysctl so HAProxy can bind to VIPs
managed by keepalived.

[`mgcdrd.infrasvc.haproxy`](roles/haproxy/README.md)

**General role variables**

| Variable                    | Default | Required | Description |
|-----------------------------|---------|----------|-------------|
| haproxy_global              | `{}`    | No       | Settings for the `global` section |
| haproxy_defaults            | `[]`    | No       | `defaults` blocks |
| haproxy_mailers             | `[]`    | No       | `mailers` blocks |
| haproxy_resolvers           | `[]`    | No       | `resolvers` blocks |
| haproxy_frontends           | `[]`    | Yes      | `frontend` blocks |
| haproxy_backends            | `[]`    | Yes      | `backend` blocks |
| haproxy_additional          | `[]`    | No       | Extra files hard-linked into place before haproxy starts |
| haproxy_selinux_connect_any | `true`  | No       | Set the SELinux boolean that lets haproxy connect to backends on non-standard ports |


Note: See [`mgcdrd.infrasvc.haproxy README.md`](roles/haproxy/README.md) for more details


ipa_baseline Role Variables
--------------

One-time bootstrap role that creates the least-privilege IPA service account
used by `ipa_client` for host pre-registration, and stores its credentials in
HashiCorp Vault.

Run this once after IPA is stood up. Re-run with `ipa_baseline_force_rotate: true`
after a Vault DR restore to regenerate and re-sync the enrollment secret.

[`mgcdrd.infrasvc.ipa_baseline`](roles/ipa_baseline/README.md)

**General role variables**

| Variable                           | Default                                | Required | Description |
|------------------------------------|----------------------------------------|----------|-------------|
| ipa_baseline_server                | `""`                                   | Yes      | FQDN of the primary IPA server |
| ipa_baseline_admin_principal       | `"admin"`                              | No       | IPA admin username used to bootstrap the service account |
| ipa_baseline_validate_certs        | `true`                                 | No       | Set to false only in lab environments with self-signed IPA certificates |
| ipa_baseline_enrollment_principal  | `"svc-ansible-enrollment"`             | No       | Username of the least-privilege enrollment service account to create/ensure |
| ipa_baseline_enrollment_role       | `"Ansible Host Enrollment"`            | No       | IPA role that will hold the Host Enrollment privilege |
| ipa_baseline_force_rotate          | `false`                                | No       | Force password rotation even when Vault already has credentials |
| ipa_baseline_vault_url             | `""`                                   | Yes      | Base URL of the Vault API, no trailing slash |
| ipa_baseline_vault_token           | *(`VAULT_TOKEN` environment variable)* | No       | Vault token used to read and write secrets |
| ipa_baseline_vault_kv_mount        | `"kv1"`                                | No       | KV engine mount point |
| ipa_baseline_vault_enrollment_path | `"ipa/enrollment"`                     | No       | Path within the KV mount where enrollment credentials are stored |
| vault_ipa_admin_password           | `""`                                   | Yes      | IPA admin password, supplied at runtime |


ipa_client Role Variables
--------------

Enrolls a host into FreeIPA. Handles DNS registration, IPA host pre-registration
via the enrollment service account (created by `ipa_baseline`), package installation,
and `ipa-client-install` execution.

Foreman provisioning remains the primary enrollment path. This role handles
everything Foreman doesn't cover: manual builds, post-provisioning DNS fixup,
and broken enrollment repair.

[`mgcdrd.infrasvc.ipa_client`](roles/ipa_client/README.md)

**General role variables**

| Variable                       | Default                                | Required | Description |
|--------------------------------|----------------------------------------|----------|-------------|
| ipa_client_servers             | `[]`                                   | Yes      | IPA server FQDNs |
| ipa_client_domain              | `""`                                   | Yes      | IPA domain (lowercase), e.g. `lab.example.com` |
| ipa_client_realm               | `""`                                   | Yes      | Kerberos realm (uppercase), e.g. `LAB.EXAMPLE.COM` |
| ipa_client_validate_certs      | `true`                                 | No       | Set to false for lab environments with self-signed IPA certificates |
| ipa_client_host_ip             | `"{{ ansible_default_ipv4.address }}"` | No       | IP address to register in PowerDNS and record on the IPA host object |
| ipa_client_pdns_api_url        | `""`                                   | If `ipa_client_dns_register` | PowerDNS authoritative API endpoint reachable from the target host |
| ipa_client_pdns_server_id      | `"localhost"`                          | No       | PowerDNS server ID — almost always "localhost" |
| ipa_client_dns_forward_zone    | `""`                                   | If `ipa_client_dns_register` | Forward zone for the A record, e.g. `lab.example.com` |
| ipa_client_dns_reverse_zone    | `""`                                   | If `ipa_client_dns_register` | Reverse zone for the PTR record, e.g. `10.0.0.in-addr.arpa` |
| ipa_client_dns_ttl             | `300`                                  | No       | TTL for registered DNS records (seconds) |
| ipa_client_dns_register        | `true`                                 | No       | Register the host in PowerDNS; set false when another process (e.g. Foreman) owns the record |
| vault_ipa_enrollment_principal | `""`                                   | Yes      | Enrollment service account written by `ipa_baseline`; inject from Vault |
| vault_ipa_enrollment_password  | `""`                                   | Yes      | Enrollment account password; inject from Vault |
| vault_ipa_pdns_api_key         | `""`                                   | If `ipa_client_dns_register` | PowerDNS API key; inject from Vault |


ipa_server Role Variables
--------------

Stands up FreeIPA itself — a fresh primary server (new domain, realm, and CA)
or a replica joined to an existing domain. A thin wrapper around the upstream
`freeipa.ansible_freeipa` collection that adds the lab's conventions: no
integrated DNS (PowerDNS stays authoritative), realm records pushed to the
PowerDNS API, secrets from Vault, Rocky Linux only.

Host enrolment for ordinary domain members is a different job — use
`mgcdrd.infrasvc.ipa_client`. Creating the least-privilege enrolment service
account is `mgcdrd.infrasvc.ipa_baseline`, run once after the primary is up.


[`mgcdrd.infrasvc.ipa_server`](roles/ipa_server/README.md)

**General role variables**

| Variable                      | Default                                | Required                      | Description |
|-------------------------------|----------------------------------------|-------------------------------|-------------|
| ipa_server_mode               | `"primary"`                            | No                            | `primary` runs `ipa-server-install` to create a new domain, realm, and CA; `replica` joins an existing one |
| ipa_server_domain             | `""`                                   | Yes                           | IPA domain (lowercase), e.g. `lab.example.com` |
| ipa_server_realm              | `""`                                   | Yes                           | Kerberos realm (uppercase), e.g. `LAB.EXAMPLE.COM` |
| ipa_server_primary            | `""`                                   | If `ipa_server_mode: replica` | FQDN of an existing IPA server to replicate from; ignored for `primary` |
| ipa_server_hostname           | `"{{ ansible_fqdn }}"`                 | No                            | FQDN this server registers itself as |
| ipa_server_setup_ca           | `true`                                 | No                            | Configure a CA on this node |
| ipa_server_mkhomedir          | `true`                                 | No                            | Create home directories on first login (pam_oddjob_mkhomedir) |
| ipa_server_validate_certs     | `true`                                 | No                            | Validate TLS certificates on the PowerDNS API calls |
| ipa_server_register_dns       | `true`                                 | No                            | Register this server's own A/PTR records in PowerDNS before the install |
| ipa_server_host_ip            | `"{{ ansible_default_ipv4.address }}"` | No                            | IP address to register for this host's A/PTR records |
| ipa_server_manage_srv_records | `true`                                 | No                            | Push the realm SRV/TXT records and the ipa-ca A record into PowerDNS |
| ipa_server_srv_hosts          | *(list, 1 items)*                      | No                            | FQDNs of every IPA server that should appear in the SRV / ipa-ca records |
| ipa_server_pdns_api_url       | `""`                                   | If DNS registration or SRV management | PowerDNS authoritative API endpoint reachable from the target host |
| ipa_server_pdns_server_id     | `"localhost"`                          | No                            | PowerDNS server ID — almost always "localhost" |
| ipa_server_dns_forward_zone   | `""`                                   | If DNS registration or SRV management | Forward zone for the A, SRV, and TXT records |
| ipa_server_dns_reverse_zone   | `""`                                   | If `ipa_server_register_dns`  | Reverse zone for the PTR record |
| ipa_server_dns_ttl            | `300`                                  | No                            | TTL for registered DNS records (seconds) |
| ipa_server_manage_acme_cert   | `false`                                | No                            | Deploy `/usr/local/sbin/acme.sh.renewal.sh`, which roots an acme.sh-issued chain and installs it as this server's IPA CA trust and httpd/LDAP cert |
| ipa_server_acme_cert_name     | `"{{ ipa_server_hostname }}"`          | No                            | acme.sh cert directory (under `/root/.acme.sh/`) the script installs when run with no argument |
| vault_ipa_admin_password      | `""`                                   | Yes                           | IPA admin (`admin@REALM`) password |
| vault_ipa_dirman_password     | `""`                                   | Yes                           | Directory Manager (`cn=Directory Manager`) password |
| vault_ipa_pdns_api_key        | `""`                                    | If DNS registration or SRV management | PowerDNS API key |


ipa_service_account Role Variables
--------------

Issues an IPA Kerberos service principal (e.g. `HTTP/<fqdn>`) and its keytab
for a service that is not an enrolled IPA client — most commonly a
containerized app with no persistent host identity — and stores the keytab
in HashiCorp Vault. Skips everything if Vault already holds a keytab at
`ipa_service_account_vault_path`, since re-issuing invalidates every
deployed copy.

Kinits as a dedicated least-privilege manager account (Host Administrators +
Service Administrators privileges, bootstrapped on first use) rather than
admin. The host running the role needs `freeipa-client` for `kinit`/
`ipa-getkeytab`.

[`mgcdrd.infrasvc.ipa_service_account`](roles/ipa_service_account/README.md)

**General role variables**

| Variable                                 | Default                                | Required                     | Description |
|------------------------------------------|----------------------------------------|------------------------------|-------------|
| ipa_service_account_server               | `""`                                   | Yes                          | FQDN of the IPA server |
| ipa_service_account_admin_principal      | `"admin"`                              | No                           | IPA admin username used to bootstrap the manager account/role |
| ipa_service_account_validate_certs       | `true`                                 | No                           | Set to false only in lab environments with self-signed IPA certificates |
| ipa_service_account_manage_manager       | `true`                                 | No                           | Create and maintain a least-privilege manager account that `kinit`s for `ipa-getkeytab`, rather than using admin |
| ipa_service_account_manager_principal    | `"svc-ipa-keytab-mgr"`                 | No                           | Shared manager account username |
| ipa_service_account_manager_role         | `"IPA Keytab Issuer"`                  | No                           | IPA role holding the manager's privileges |
| ipa_service_account_force_rotate_manager | `false`                                | No                           | Regenerate the manager account's password even if Vault already has one |
| ipa_service_account_fqdn                 | `""`                                   | Yes                          | FQDN the service principal is issued for |
| ipa_service_account_principal_type       | `"HTTP"`                               | No                           | Kerberos service type, e.g. `HTTP` for `HTTP/<fqdn>` |
| ipa_service_account_force_rotate         | `false`                                | No                           | Re-fetch the keytab even if one exists; rotates the key, invalidating earlier copies |
| ipa_service_account_vault_url            | `""`                                   | Yes                          | Base URL of the Vault API, no trailing slash |
| ipa_service_account_vault_token          | *(`VAULT_TOKEN` environment variable)* | No                           | Vault token used to read and write secrets |
| ipa_service_account_vault_kv_mount       | `"kv1"`                                | No                           | KV engine mount point |
| ipa_service_account_vault_manager_path   | `"ipa/service-account-manager"`        | No                           | KV path holding the manager account's credentials; shared across every caller |
| ipa_service_account_vault_path           | `""`                                   | Yes                          | KV path the issued keytab is written to (`fqdn`, `principal`, `keytab_b64`); one per service |
| vault_ipa_admin_password                 | `""`                                   | If bootstrapping the manager | IPA admin password; needed only the first time the manager account is created |


k8s Role Variables
--------------

Provisions a Kubernetes cluster across Debian and Rocky Linux nodes. Handles
node preparation (swap, sysctl, kernel modules, NetworkManager, `/etc/hosts`),
container runtime install, Kubernetes repo/package install, control plane
initialization with Calico CNI, worker/additional-master joins, keepalived
for HA VIP, and helm + Python kubernetes library on masters for platform
bootstrap.

[`mgcdrd.infrasvc.k8s`](roles/k8s/README.md)

**General role variables**

| Variable                   | Default                  | Required | Description |
|----------------------------|--------------------------|----------|-------------|
| k8s_version                | `"1.32"`                 | No       | Kubernetes minor version; also passed to the container runtime role |
| k8s_calico_version         | `"3.31.0"`               | No       | Calico CNI version |
| k8s_svc_cidr               | `"10.96.0.0/12"`         | No       | Kubernetes service CIDR |
| k8s_pod_cidr               | `"10.112.0.0/12"`        | No       | Pod network CIDR |
| k8s_selinux_state          | `Permissive`             | No       | SELinux state on RedHat nodes |
| k8s_firewalld_ports_common | *(list, 2 items)*        | No       | Ports opened on every node (firewalld) |
| k8s_firewalld_ports_master | *(list, 4 items)*        | No       | Ports opened on control plane nodes only |
| k8s_firewalld_ports_worker | *(list, 1 items)*        | No       | Ports opened on worker nodes only |
| k8s_modules                | *(list, 2 items)*        | No       | Kernel modules loaded on all nodes during prep (`br_netfilter`, `overlay`) |
| k8s_sysctl                 | *(list, 5 items)*        | No       | sysctl parameters written to `/etc/sysctl.d/kubernetes.conf` during prep |
| k8s_container_runtime      | `cri-o`                  | No       | Runtime to install: `cri-o`, `docker`, or `podman` (only `cri-o` is fully supported) |
| k8s_run                    | `config`                 | No       | Phase to run: `config` (node prep), `init` (`kubeadm init`, Calico, join), or `addnodes` (join an existing cluster) |
| k8s_advertise_address      | *(primary IPv4 address)* | No       | IP the API server binds to and advertises in `InitConfiguration` |
| k8s_cluster_group          | `""`                     | No       | Inventory group written to `/etc/hosts` on every node; auto-detected when empty |
| k8s_helm_version           | `3`                      | No       | Helm major version installed on masters: `3` or `4` |
| k8s_psa_enabled            | `true`                   | No       | Apply cluster-wide Pod Security Admission defaults through `AdmissionConfiguration` |
| k8s_psa_version            | `latest`                 | No       | Policy version the PSA levels are pinned to |
| k8s_psa_enforce            | `baseline`               | No       | PSA level enforced by default |
| k8s_psa_warn               | `restricted`             | No       | PSA level that warns by default |
| k8s_psa_audit              | `restricted`             | No       | PSA level recorded in audit logs by default |
| k8s_psa_exempt_namespaces  | *(list, 3 items)*        | No       | Namespaces exempt from the PSA defaults |
| k8s_oidc_enabled           | `false`                  | No       | Configure the API server to accept JWTs from an external OIDC provider (e.g. Keycloak) |
| k8s_oidc_issuer_url        | `""`                     | If `k8s_oidc_enabled` | OIDC issuer URL, e.g. `https://infra-kc.example.com/realms/lab` |
| k8s_oidc_client_id         | `"kubernetes"`           | No       | OIDC client ID |
| k8s_oidc_username_claim    | `"preferred_username"`   | No       | JWT claim used as the Kubernetes username |
| k8s_oidc_groups_claim      | `"groups"`               | No       | JWT claim used for group membership |
| k8s_keepalived_enabled     | `false`                  | No       | Mirror of the deployment-level keepalived flag; stops keepalived on joining nodes so the VIP stays on the init master |
| k8s_init_master            | `""`                     | Yes      | FQDN of the node that runs `kubeadm init`; all other masters join after it |
| k8s_control_plane_endpoint | `""`                     | Yes      | DNS name or VIP for the HA API endpoint, used in the kubeadm config and cert SANs |
| k8s_init_token             | `unset`                  | No       | Pins the `kubeadm init` bootstrap token (`[a-z0-9]{6}.[a-z0-9]{16}`); unset lets kubeadm generate one. Treat as a secret, inject from Vault |


keepalived Role Variables
--------------

Installs and configures keepalived with VRRP instances, preset health-check
scripts, and automatic node priority calculation.

Supports multi-node clusters. The master node receives `keepalived_priority_max`
(210) and priorities are spread linearly down to `keepalived_priority_min` (90)
across backup nodes. Existing VRRP auth passwords are preserved across runs by
reading the current config before writing.

[`mgcdrd.infrasvc.keepalived`](roles/keepalived/README.md)

**General role variables**

| Variable                         | Default           | Required | Description |
|----------------------------------|-------------------|----------|-------------|
| vrrp_script_interval             | `3`               | No       | Seconds between runs of any `vrrp_script` that does not set its own |
| vrrp_script_fall                 | `3`               | No       | Consecutive failures before a script is marked failed |
| vrrp_script_rise                 | `4`               | No       | Consecutive successes before a script is marked healthy |
| vrrp_script_init_fail            | `true`            | No       | Start scripts in the failed state until they first succeed |
| vrrp_script_user                 | `root`            | No       | User scripts run as |
| vrrp_script_group                | `root`            | No       | Group scripts run as |
| keepalived_priority_max          | `210`             | No       | VRRP priority of the first node (master); priorities step down linearly to the minimum |
| keepalived_priority_min          | `90`              | No       | VRRP priority of the last backup |
| keepalived_script_weight_default | `"-150"`          | No       | Weight applied on script failure when a script does not set one |
| keepalived_vip_for               | `[]`              | No       | Presets to activate: `webproxy`, `ftp`, `kubernetes`, `dockerswarm`, `keycloak` |
| keepalived_global_defs           | `{}`              | No       | `global_defs` block; empty omits it |
| keepalived_vrrp_scripts          | `[]`              | No       | Extra `vrrp_script` entries beyond the presets |
| keepalived_vrrp_instances        | `[]`              | Yes      | `vrrp_instance` definitions (fields below); the role does nothing without them |
| keepalived_preset_webproxy       | *(map, 11 lines)* | No       | Built-in `webproxy` preset (scripts and instance); redefine to override |
| keepalived_preset_ftp            | *(map, 11 lines)* | No       | Built-in `ftp` preset; redefine to override |
| keepalived_preset_dockerswarm    | *(map, 21 lines)* | No       | Built-in `dockerswarm` preset; redefine to override |
| keepalived_preset_kubernetes     | *(map, 11 lines)* | No       | Built-in `kubernetes` preset; redefine to override |
| keepalived_preset_keycloak       | *(map, 11 lines)* | No       | Built-in `keycloak` preset; redefine to override |


**keepalived_vip_for[] variables**

| Option      | Script placed on host                         | Checks |
|-------------|-----------------------------------------------|--------|
| webproxy    | `/etc/keepalived/check_nginx.sh`              | nginx process |
| ftp         | `/etc/keepalived/check_haproxy.sh`            | haproxy process |
| kubernetes  | `/etc/keepalived/check_apiserver.sh`          | k8s API server |
| dockerswarm | `check_node_active.sh`, `check_node_ready.sh` | swarm node state |
| keycloak    | `/etc/keepalived/check_keycloak.sh`           | Keycloak `/health/ready` on the management port |




keycloak Role Variables
--------------

Deploys Keycloak (Quarkus) with a PostgreSQL backend and acme.sh TLS, one
of two ways:

- `docker` (default) — a single Keycloak service via Docker Compose, `host`
  or `bridge` networking. Active/passive with keepalived (`KC_CACHE` stays
  `local`).
- `native` — the Keycloak tarball under a hardened systemd unit.
  Infinispan clusters over `jdbc-ping` (database discovery, no multicast),
  which makes cross-node caching work inside an unprivileged LXC. Binds
  `:443` directly; adds no firewalld rules.

Also ships `keepalived_preset_keycloak`, which the `keepalived` role picks
up when `keepalived_vip_for` includes `keycloak`.

[`mgcdrd.infrasvc.keycloak`](roles/keycloak/README.md)

**General role variables**

| Variable                                     | Default                                                 | Required                             | Description |
|----------------------------------------------|---------------------------------------------------------|--------------------------------------|-------------|
| keycloak_install_method                      | `docker`                                                | No                                   | `docker` (Compose stack) or `native` (Quarkus tarball with a hardened systemd unit, e.g. for LXC) |
| keycloak_hostname                            | `""`                                                    | Yes                                  | External FQDN served by the keepalived VIP; used in the TLS cert and `KC_HOSTNAME` |
| keycloak_version                             | `"26.4"`                                                | No                                   | Container image tag (floating); docker only |
| keycloak_image                               | `"quay.io/keycloak/keycloak"`                           | No                                   | Container image repository; docker only |
| keycloak_network_mode                        | `host`                                                  | Yes                                  | `host` (recommended) or `bridge` (cross-host clustering then needs `KC_CACHE_STACK=tcp` via `keycloak_extra_env`); docker only |
| keycloak_http_port                           | `8080`                                                  | No                                   | HTTP bind port; use an unprivileged port |
| keycloak_https_port                          | `443` native, `8443` docker                             | No                                   | HTTPS bind port; firewalld forwards 443 to it |
| keycloak_mgmt_port                           | `9000`                                                  | No                                   | Health and metrics endpoint port |
| keycloak_jgroups_port                        | `7800`                                                  | No                                   | Infinispan JGroups cluster traffic port |
| keycloak_jgroups_fd_port                     | `57600`                                                 | No                                   | JGroups failure-detection (FD_SOCK) port |
| keycloak_base_dir                            | `/srv/docker/keycloak`                                  | No                                   | Base directory for the compose file; docker only |
| keycloak_shared_storage                      | `nfs`                                                   | Yes                                  | Where themes and truststores live: `nfs` (shared between HA nodes) or `local` (under `keycloak_base_dir/data`); docker only |
| keycloak_nfs_server                          | `""`                                                    | If `keycloak_shared_storage: nfs`    | NFS server address |
| keycloak_nfs_path                            | `""`                                                    | If `keycloak_shared_storage: nfs`    | NFS export path |
| keycloak_nfs_mount                           | `/mnt/keycloak`                                         | No                                   | Local mount point for the NFS share |
| keycloak_nfs_opts                            | `"vers=3,_netdev"`                                      | No                                   | NFS mount options |
| keycloak_data_subdirs                        | *(list, 2 items)*                                       | No                                   | Subdirectories created under the data root |
| keycloak_extra_env                           | `{}`                                                    | No                                   | Additional `KC_*` environment variables merged into the compose service; docker only |
| postgres_version                             | `"18"`                                                  | No                                   | PostgreSQL image tag; docker only |
| postgres_image                               | `"postgres"`                                            | No                                   | PostgreSQL image repository; docker only |
| postgres_db                                  | `keycloak`                                              | No                                   | Database name |
| postgres_host                                | `""`                                                    | Yes                                  | FQDN or IP of the PostgreSQL host |
| postgres_port                                | `5432`                                                  | No                                   | PostgreSQL port |
| postgres_admin_user                          | `postgres`                                              | No                                   | Admin account used to create the database and grant scoped access to `keycloak_db_user` |
| postgres_admin_password                      | `{{ vault_postgres_admin_password }}`                   | No                                   | Password for the admin account |
| keycloak_db_user                             | `{{ vault_keycloak_db_user }}`                          | No                                   | Database user Keycloak connects as |
| keycloak_db_password                         | `{{ vault_keycloak_db_password }}`                      | No                                   | Password for `keycloak_db_user` |
| keycloak_db_sslmode                          | `verify-full`                                           | No                                   | Keycloak to PostgreSQL TLS mode in the JDBC URL; native only |
| keycloak_db_sslrootcert                      | `{{ keycloak_install_dir }}/conf/truststores/db-ca.pem` | No                                   | CA file checked by `verify-full`; native only |
| keycloak_admin_user                          | `{{ vault_keycloak_admin_user }}`                       | No                                   | Bootstrap admin username; only active on first start |
| keycloak_admin_password                      | `{{ vault_keycloak_admin_password }}`                   | No                                   | Bootstrap admin password; only active on first start |
| keycloak_release                             | `""`                                                    | If `keycloak_install_method: native` | Full `X.Y.Z` release (the GitHub tag); `keycloak_version` will not resolve a tarball |
| keycloak_download_url                        | *(GitHub release URL for `keycloak_release`)*           | No                                   | Tarball URL; override for a mirror |
| keycloak_download_checksum                   | `""`                                                    | No                                   | Checksum for the tarball, e.g. `sha256:https://…/keycloak-<ver>.tar.gz.sha256` |
| keycloak_service_name                        | `keycloak`                                              | No                                   | systemd unit name; native only |
| keycloak_service_user                        | `keycloak`                                              | No                                   | Service user; native only |
| keycloak_service_group                       | `keycloak`                                              | No                                   | Service group; native only |
| keycloak_install_dir                         | `/opt/keycloak`                                         | No                                   | Install path, a symlink to the versioned directory; native only |
| keycloak_versioned_dir                       | `"/opt/keycloak-{{ keycloak_release }}"`                | No                                   | Versioned install directory; native only |
| keycloak_systemd_hardening                   | `true`                                                  | No                                   | Emit the sandboxing block in the unit; native only |
| keycloak_java_package_method                 | `distro`                                                | No                                   | `distro` (OS OpenJDK 21) or `adoptium` (Eclipse Temurin); native only |
| keycloak_java_package                        | *(OS-specific OpenJDK 21 package)*                      | No                                   | Distro JDK package; override for a newer JDK |
| keycloak_adoptium_package                    | `temurin-21-jdk`                                        | No                                   | Package installed when `keycloak_java_package_method: adoptium` |
| keycloak_http_enabled                        | `false`                                                 | No                                   | Enable the plain HTTP listener; native only |
| keycloak_https_protocols                     | `"TLSv1.3,TLSv1.2"`                                     | No                                   | Allowed TLS protocols; native only |
| keycloak_hostname_strict                     | `true`                                                  | No                                   | Enforce the configured hostname; native only |
| keycloak_metrics_enabled                     | `false`                                                 | No                                   | Enable the metrics endpoint; native only |
| keycloak_cache                               | `ispn`                                                  | No                                   | Infinispan cache mode; native only |
| keycloak_cache_stack                         | `jdbc-ping`                                             | No                                   | Cache discovery stack; native only |
| keycloak_cache_embedded_mtls_enabled         | `true`                                                  | No                                   | mTLS on the JGroups transport; native only |
| keycloak_cache_embedded_network_bind_address | *(default IPv4 address, else `127.0.0.1`)*              | No                                   | JGroups bind address; native only |
| keycloak_truststore_files                    | `[]`                                                    | No                                   | Files placed in `{{ keycloak_install_dir }}/conf/truststores/` |
| keycloak_extra_conf                          | `{}`                                                    | No                                   | Extra `key=value` lines appended to `keycloak.conf`; native only |
| keycloak_manage_tls                          | `true`                                                  | No                                   | Issue the TLS certificate with `mgcdrd.infrabase.acme_sh`; false when TLS terminates upstream |
| acme_sh_cert_base_dir                        | `/etc/ssl/acme`                                         | No                                   | Where `acme_sh` deploys certs; must match the `acme_sh` role's value |
| keycloak_cert_dir                            | `{{ acme_sh_cert_base_dir }}/{{ keycloak_hostname }}`   | No                                   | Directory holding this host's certificate |
| keycloak_acme_challenge                      | `dns_cf`                                                | No                                   | `acme_sh` challenge type: `dns_cf`, `dns_pdns`, `standalone`, `webroot`, … |
| keycloak_acme_complete_chain                 | `false`                                                 | No                                   | Root the deployed chain with a pinned root (needed for Google Public CA) |
| keycloak_acme_root_cn                        | `""`                                                    | No                                   | Root CA common name for `complete_chain`; empty uses the `acme_sh` default |
| keycloak_acme_root_fingerprint               | `""`                                                    | No                                   | Root CA fingerprint for `complete_chain`; empty uses the `acme_sh` default |
| keycloak_acme_root_urls                      | `[]`                                                    | No                                   | Root CA PEM URLs for `complete_chain`; empty uses the `acme_sh` default |
| keepalived_preset_keycloak                   | *(map, 11 lines)*                                       | No                                   | Keepalived preset registered for the `keepalived` role |


Note: CA selection, EAB, and DNS-provider credentials are `acme_sh` role variables — set them at the deployment/inventory level


keycloak_config Role Variables
--------------

Configures Keycloak post-deploy via the REST API; Keycloak must already be
running and healthy. On the master realm it sets up read-only LDAP
federation and grants the `admin` realm role to LDAP groups. On the lab
realm it creates the realm, its own LDAP federation, the `kubernetes` OIDC
client (groups and `preferred_username` mappers, `cluster-admin` client
role), and binds that role to LDAP groups.

Each realm section is gated by a boolean and a tag (`kc_master`,
`kc_lab`) so it can be re-run alone.

[`mgcdrd.infrasvc.keycloak_config`](roles/keycloak_config/README.md)

**General role variables**

| Variable                                      | Default                                     | Required | Description |
|-----------------------------------------------|---------------------------------------------|----------|-------------|
| keycloak_config_auth_url                      | `https://localhost:<keycloak_https_port>`   | No       | URL used to reach the Keycloak admin API; local by default so tasks skip the VIP |
| keycloak_config_validate_certs                | `false`                                     | No       | Validate the Keycloak API TLS certificate |
| keycloak_config_admin_user                    | `{{ vault_keycloak_admin_user }}`           | No       | Admin user |
| keycloak_config_admin_password                | `{{ vault_keycloak_admin_password }}`       | No       | Admin password |
| keycloak_ldap_url                             | `""`                                        | Yes      | LDAP server URL, `ldap://` or `ldaps://` |
| keycloak_ldap_bind_dn                         | `""`                                        | Yes      | DN of the bind account |
| keycloak_ldap_bind_credential                 | `{{ vault_keycloak_ldap_bind_credential }}` | Yes      | Bind account password |
| keycloak_ldap_users_dn                        | `""`                                        | Yes      | Base DN users are searched under |
| keycloak_ldap_vendor                          | `"ad"`                                      | No       | `ad`, or `other` for OpenLDAP/FreeIPA |
| keycloak_ldap_edit_mode                       | `"READ_ONLY"`                               | No       | `READ_ONLY`, `WRITABLE`, or `UNSYNCED` |
| keycloak_ldap_username_ldap_attribute         | `"sAMAccountName"`                          | No       | LDAP attribute mapped to the username (`uid` for OpenLDAP/FreeIPA) |
| keycloak_ldap_rdn_ldap_attribute              | `"cn"`                                      | No       | RDN attribute of user entries |
| keycloak_ldap_uuid_ldap_attribute             | `"objectGUID"`                              | No       | Unique ID attribute (`entryUUID` for OpenLDAP) |
| keycloak_ldap_user_object_classes             | `"person, organizationalPerson, user"`      | No       | Object classes identifying user entries |
| keycloak_ldap_search_scope                    | `"2"`                                       | No       | `1` one level, `2` subtree |
| keycloak_ldap_connection_timeout              | `5000`                                      | No       | Connection timeout in ms |
| keycloak_ldap_read_timeout                    | `10000`                                     | No       | Read timeout in ms |
| keycloak_ldap_pagination                      | `true`                                      | No       | Use paged LDAP results |
| keycloak_ldap_connection_pooling              | `true`                                      | No       | Pool LDAP connections |
| keycloak_ldap_start_tls                       | `false`                                     | No       | Use StartTLS on the connection |
| keycloak_ldap_use_truststore_spi              | `"ldapsOnly"`                               | No       | When the Keycloak truststore is used for LDAP TLS: `ldapsOnly`, `always`, or `never` |
| keycloak_ldap_sync_registrations              | `false`                                     | No       | Write users registered in Keycloak back to LDAP |
| keycloak_ldap_full_sync_period                | `-1`                                        | No       | Seconds between full syncs; `-1` disables |
| keycloak_ldap_changed_sync_period             | `-1`                                        | No       | Seconds between changed-user syncs; `-1` disables |
| keycloak_ldap_groups_dn                       | `""`                                        | Yes      | Base DN groups are searched under |
| keycloak_ldap_group_object_classes            | `"group"`                                   | No       | Object classes identifying group entries (`groupOfNames` for OpenLDAP) |
| keycloak_ldap_group_membership_attribute      | `"member"`                                  | No       | Group attribute listing its members |
| keycloak_ldap_group_membership_attribute_type | `"DN"`                                      | No       | `DN` or `UID` |
| keycloak_ldap_groups_ldap_filter              | `""`                                        | No       | Optional LDAP filter limiting which groups are imported |
| keycloak_ldap_groups_path                     | `"/"`                                       | No       | Keycloak group path imported groups are created under |
| keycloak_ldap_drop_non_existing_groups        | `false`                                     | No       | Drop Keycloak groups that no longer exist in LDAP |
| keycloak_ldap_preserve_group_inheritance      | `true`                                      | No       | Keep LDAP group nesting as Keycloak subgroups |
| keycloak_configure_master                     | `true`                                      | No       | Configure the master realm; false skips the section |
| keycloak_configure_lab                        | `true`                                      | No       | Configure the lab realm (LDAP, k8s client, group bindings); false skips the section |
| keycloak_master_admin_groups                  | `[]`                                        | No       | LDAP groups granted the `admin` realm role on the master realm |
| keycloak_lab_realm_name                       | `"lab"`                                     | No       | Lab realm name |
| keycloak_lab_realm_display                    | `"Lab"`                                     | No       | Lab realm display name |
| keycloak_lab_ssl_required                     | `"external"`                                | No       | Realm `sslRequired`: `none`, `external`, or `all` |
| keycloak_lab_session_idle                     | `1800`                                      | No       | SSO session idle timeout in seconds |
| keycloak_lab_session_max                      | `36000`                                     | No       | SSO session maximum lifespan in seconds |
| keycloak_lab_token_lifespan                   | `300`                                       | No       | Access token lifespan in seconds |
| keycloak_lab_admin_groups                     | `[]`                                        | No       | LDAP groups granted the Kubernetes cluster-admin role in the lab realm |
| keycloak_lab_extra_groups                     | `[]`                                        | No       | Additional LDAP groups to ensure exist in the lab realm |
| keycloak_k8s_client_id                        | `"kubernetes"`                              | No       | OIDC client ID for Kubernetes; must match `k8s_oidc_client_id` |
| keycloak_k8s_client_name                      | `"Kubernetes"`                              | No       | Display name of the Kubernetes client |
| keycloak_k8s_public_client                    | `true`                                      | No       | Public client with no secret (recommended for kubectl) |
| keycloak_k8s_redirect_uris                    | *(list, 1 items)*                           | No       | Allowed redirect URIs for the Kubernetes client |
| keycloak_k8s_web_origins                      | *(list, 1 items)*                           | No       | Allowed web origins for the Kubernetes client |


nginx Role Variables
--------------

Installs and configures nginx. Manages `/etc/nginx/nginx.conf`, per-site server
block configs under `/etc/nginx/conf.d/`, and a set of shared config snippets
(SSL hardening, proxy headers, logging, user-agent blocking) deployed to
`/etc/nginx/conf.d/shared_configs/`.

[`mgcdrd.infrasvc.nginx`](roles/nginx/README.md)

**General role variables**

| Variable                              | Default                            | Required | Description |
|---------------------------------------|------------------------------------|----------|-------------|
| nginx_process_user                    | `nginx`                            | No       | `user` directive |
| nginx_worker_processes                | `auto`                             | No       | `worker_processes` |
| nginx_pid_file                        | `/run/nginx.pid`                   | No       | `pid` file path |
| nginx_load_dynamic_mods               | `false`                            | No       | Emit `load_module` lines for dynamic modules |
| nginx_events                          | *(map, 1 lines)*                   | No       | `events` block settings |
| nginx_http_block                      | *(map, 9 lines)*                   | No       | `http` block settings (logging, timeouts, TLS, security headers); see `vars/main.yml` for the annotated structure |
| nginx_badagent_list                   | *(map, 10 items)*                  | No       | If `nginx_http_block.block_badagents` sets a defined list of user agent allow/deny |
| nginx_shared_configs                  | `{}`                               | No       | Variables consumed by the `shared_configs/*.conf.j2` templates |
| nginx_server_blocks                   | `[]`                               | Yes      | Server block definitions, one conf file per entry (fields below) |
| nginx_conf_d_dir                      | `/etc/nginx/conf.d`                | No       | Base `conf.d` directory; override for a nonstandard install |
| nginx_proxy_files_dir                 | `"{{ nginx_conf_d_dir }}/proxies"` | No       | Directory of per-server-block proxy files owned by another team, kept separate from this role's server block shell |
| nginx_proxy_files_group               | `""`                               | If any server block has `exclude_proxy_files: false` | Group that owns `nginx_proxy_files_dir` and the placeholder files in it |
| nginx_proxy_sync_enabled              | `false`                            | No       | Pull proxy files from S3-compatible storage on a timer instead of editing them on the node |
| nginx_proxy_sync_interval             | `5min`                             | No       | systemd time span between pulls |
| nginx_proxy_sync_s3_endpoint          | `""`                               | If `nginx_proxy_sync_enabled` | Path-style S3 endpoint (MinIO, Ceph RGW), e.g. `https://s3.example.com:9000` |
| nginx_proxy_sync_s3_bucket            | `""`                               | If `nginx_proxy_sync_enabled` | Bucket holding the proxy files |
| nginx_proxy_sync_s3_prefix            | `""`                               | No       | Key prefix under the bucket; files are `<prefix>/<server block name>.proxies` |
| nginx_proxy_sync_s3_region            | `us-east-1`                        | No       | S3 region |
| nginx_proxy_sync_s3_ca_file           | `""`                               | No       | CA bundle for a private-CA endpoint |
| nginx_proxy_sync_vault_addr           | `"{{ vault_addr }}"`               | No       | Vault address the S3 credentials are read from at runtime (AppRole) |
| nginx_proxy_sync_vault_secret_path    | *(see defaults)*                   | If `nginx_proxy_sync_enabled` | Vault KV v2 API path (mount and `/data/` included) holding `access_key` and `secret_key` |
| nginx_proxy_sync_vault_role_id_file   | `/etc/vault/webproxy-s3-role-id`   | No       | AppRole role_id file, pre-positioned on the host |
| nginx_proxy_sync_vault_secret_id_file | `/etc/vault/webproxy-s3-secret-id` | No       | AppRole secret_id file, pre-positioned on the host |
| nginx_proxy_sync_state_dir            | `/var/lib/nginx-proxy-sync`        | No       | Holds the lock file, last-good backups, and rejected-file hashes |
| nginx_ssl_enable                      | `false`                            | No       | Enable SSL cert management |
| nginx_ssl_provider                    | `""`                               | If `nginx_ssl_enable` | Role that manages certs: `acme_sh` or `ssl_scripting` |
| nginx_ssl_scripting                   | `{}`                               | No       | Variables passed to `ssl_scripting` when `nginx_ssl_provider: ssl_scripting` |
| nginx_dhparam_bits                    | `2048`                             | No       | dhparam size when `ssl_dhparam` is set and the provider is `acme_sh` or empty |

nut_client Role Variables
--------------

Installs and configures NUT (Network UPS Tools) in secondary/client mode:
`upsmon` polling one or more remote `upsd` servers over the network. No
local driver and no `upsd` — this host never owns a UPS directly.

Client half of a pair with `mgcdrd.infrasvc.nut_server`. Shutdown is not
wired here; tiered shed logic hooks in through `nut_client_notify_hook`
(see `mgcdrd.infrasvc.ups_shed`).

[`mgcdrd.infrasvc.nut_client`](roles/nut_client/README.md)

**General role variables**

| Variable               | Default                          | Required | Description |
|------------------------|----------------------------------|----------|-------------|
| nut_client_config_dir  | `/etc/nut` Debian, `/etc/ups` EL | No       | NUT config directory; differs by packaging |
| nut_client_mode        | `netclient`                      | No       | `MODE` in `nut.conf`; `netclient` polls a remote upsd |
| nut_client_monitors    | `[]`                             | Yes      | Remote UPSes this host watches (fields below) |
| nut_client_minsupplies | `1`                              | No       | `MINSUPPLIES`: power supplies that must stay up before shutdown |
| nut_client_deadtime    | `60`                             | No       | `DEADTIME` in seconds before an unreachable upsd counts as dead; generous because the link crosses a network boundary |
| nut_client_notifycmd   | `/usr/local/bin/nut-notify.sh`   | No       | Script upsmon runs on events (deployed by the role) |
| nut_client_notify_hook | `""`                             | No       | Extra script `nut-notify.sh` calls after logging, with the same `NOTIFYTYPE` and message |
| nut_client_shutdowncmd | `""`                             | No       | `SHUTDOWNCMD`; deliberately unset so shutdown is driven by Ansible via `ups_shed` |
| nut_client_group       | `nut`                            | No       | Group NUT's upsmon runs as; matches `nut_server_group` |

**nut_client_monitors[] variables**

| Field            | Required | Description |
|------------------|----------|-------------|
| ups_name         | Yes      | UPS name as defined on the remote upsd. |
| ups_host         | Yes      | Host running upsd. |
| power_value      | Yes      | Number of power supplies this UPS feeds on this host. |
| monuser          | Yes      | upsd user to log in as (`nut_server_monuser_user`). |
| monuser_password | Yes      | Its password. Source from `{{ vault_<name> }}`. |
| role             | No       | NUT monitor role. Default: `secondary`. |


nut_server Role Variables
--------------

Installs and configures NUT in primary/server mode: the local driver talking
to a USB-attached UPS, `upsd` serving status to network clients, and (by
default) a local `upsmon` monitoring that same `upsd`.

Primary half of a pair with `mgcdrd.infrasvc.nut_client`.

[`mgcdrd.infrasvc.nut_server`](roles/nut_server/README.md)

**General role variables**

| Variable                             | Default                          | Required | Description |
|--------------------------------------|----------------------------------|----------|-------------|
| nut_server_config_dir                | `/etc/nut` Debian, `/etc/ups` EL | No       | NUT config directory; differs by packaging |
| nut_server_ups_name                  | `apc`                            | No       | UPS name in `ups.conf` |
| nut_server_ups_desc                  | `"APC Back-UPS 1500"`            | No       | UPS description in `ups.conf` |
| nut_server_driver                    | `usbhid-ups`                     | No       | NUT driver in `ups.conf` |
| nut_server_port                      | `auto`                           | No       | Driver port in `ups.conf`; `auto` for USB |
| nut_server_pollinterval              | `15`                             | No       | Driver poll interval in seconds |
| nut_server_mode                      | `netserver`                      | No       | `MODE` in `nut.conf`; `netserver` exposes upsd to the network |
| nut_server_listen_addresses          | *(list, 1 items)*                | No       | Addresses `upsd` listens on (`address`, `port`); default `0.0.0.0:3493` |
| nut_server_admin_user                | `admin`                          | No       | Admin user in `upsd.users`; can `SET` variables and issue FSD and instant commands |
| nut_server_admin_password            | `""`                             | Yes      | Admin user password; use `{{ vault_* }}` |
| nut_server_admin_actions             | `"SET FSD"`                      | No       | Actions granted to the admin user |
| nut_server_admin_instcmds            | `"ALL"`                          | No       | Instant commands granted to the admin user |
| nut_server_monuser_user              | `monuser`                        | No       | Read-only monitoring user that clients log in as |
| nut_server_monuser_password          | `""`                             | Yes      | Monitoring user password; use `{{ vault_* }}` |
| nut_server_local_monitor             | `true`                           | No       | Also run `upsmon` on this host against its own upsd, in NUT's primary role |
| nut_server_local_monitor_power_value | `1`                              | No       | Power value of the local monitor entry |
| nut_server_shutdowncmd               | `"/sbin/shutdown -h now"`        | No       | Command the local `upsmon` runs to shut the host down |
| nut_server_deadtime                  | `15`                             | No       | Local `upsmon` `DEADTIME` in seconds |
| nut_server_minsupplies               | `1`                              | No       | Local `upsmon` `MINSUPPLIES` |
| nut_server_group                     | `nut`                            | No       | Group NUT services drop privileges to; files with secrets stay group-readable by it |


pdns_phpipam Role Variables
--------------

Deploys a PowerDNS (Authoritative + Recursor + DNSDist) and phpIPAM stack via
Docker Compose, with a shared MariaDB backend and an optional nginx TLS
frontend for phpIPAM. DNSDist is the front door on port 53, routing the
domain and its reverse zone to Auth and everything else to Recursor.
Optional Galera clustering for MariaDB.

Secrets left empty are auto-generated and persisted on the controller under
`pdns_phpipam_secrets_dir` — supply them from `{{ vault_<name> }}` instead
to keep them off the controller.

[`mgcdrd.infrasvc.pdns_phpipam`](roles/pdns_phpipam/README.md)

**General role variables**

| Variable                                     | Default                                          | Required                                    | Description |
|----------------------------------------------|--------------------------------------------------|---------------------------------------------|-------------|
| pdns_phpipam_domain                          | `"lab.example.com"`                              | Yes                                         | Primary forward DNS zone |
| pdns_phpipam_domain_ip_rev                   | *(lab-specific; see defaults)*                   | Yes                                         | Reverse zone prefix for the network (first three octets) |
| pdns_phpipam_base_dir                        | `/srv`                                           | No                                          | Base directory on the host |
| pdns_phpipam_runtime_dir                     | `"{{ pdns_phpipam_base_dir }}/phpipam"`          | No                                          | Runtime directory for the compose stack |
| pdns_phpipam_mariadb_dir                     | `"{{ pdns_phpipam_runtime_dir }}/mariadb"`       | No                                          | MariaDB data directory |
| pdns_phpipam_auth_dir                        | `"{{ pdns_phpipam_runtime_dir }}/pdns_auth"`     | No                                          | PowerDNS Authoritative config directory |
| pdns_phpipam_recu_dir                        | `"{{ pdns_phpipam_runtime_dir }}/pdns_recursor"` | No                                          | PowerDNS Recursor config directory |
| pdns_phpipam_dist_dir                        | `"{{ pdns_phpipam_runtime_dir }}/pdns_dnsdist"`  | No                                          | dnsdist config directory |
| pdns_phpipam_auth_api_port                   | `0`                                              | If running `pdns_records` from another host | Host port exposing PowerDNS Authoritative's HTTP API; `0` does not expose it |
| pdns_phpipam_recu_api_port                   | `0`                                              | No                                          | Host port exposing the Recursor's HTTP API; `0` does not expose it |
| pdns_phpipam_dist_api_port                   | `0`                                              | No                                          | Host port exposing dnsdist's HTTP API; `0` does not expose it |
| pdns_phpipam_ssl_enabled                     | `false`                                          | No                                          | Add an nginx container that terminates TLS in front of phpIPAM web |
| pdns_phpipam_ssl_cert_dir                    | `""`                                             | If `pdns_phpipam_ssl_enabled`               | Path to the `acme_sh` cert directory, e.g. `/etc/ssl/acme/dns.lab.example.com` |
| pdns_phpipam_ssl_hostname                    | `""`                                             | No                                          | `ServerName` and TLS SNI; empty uses `inventory_hostname` |
| pdns_phpipam_ssl_dir                         | `"{{ pdns_phpipam_runtime_dir }}/nginx"`         | No                                          | Host directory the nginx SSL config is written to |
| pdns_phpipam_ca_certs_dir                    | `""`                                             | No                                          | Host CA bundle directory mounted into phpIPAM web; empty auto-detects by OS family |
| pdns_phpipam_docker_network_name             | `dns_net`                                        | No                                          | Docker network name |
| pdns_phpipam_docker_network_cidr             | `"10.5.0.0/16"`                                  | No                                          | Docker network CIDR |
| pdns_phpipam_docker_network_gateway          | `"10.5.0.1"`                                     | No                                          | Docker network gateway |
| pdns_phpipam_docker_network_mariadb          | `"10.5.0.2"`                                     | No                                          | Fixed IP of the MariaDB container |
| pdns_phpipam_docker_network_auth             | `"10.5.0.3"`                                     | No                                          | Fixed IP of the PowerDNS Authoritative container |
| pdns_phpipam_docker_network_recu             | `"10.5.0.4"`                                     | No                                          | Fixed IP of the PowerDNS Recursor container |
| pdns_phpipam_docker_network_dist             | `"10.5.0.5"`                                     | No                                          | Fixed IP of the dnsdist container |
| pdns_phpipam_docker_network_ipam_web         | `"10.5.0.6"`                                     | No                                          | Fixed IP of the phpIPAM web container |
| pdns_phpipam_docker_network_nginx            | `"10.5.0.7"`                                     | No                                          | Fixed IP of the nginx TLS container |
| pdns_phpipam_mariadb_pdns_db                 | `pdns`                                           | No                                          | PowerDNS database name |
| pdns_phpipam_mariadb_pdns_user               | `pdns`                                           | No                                          | PowerDNS database user |
| pdns_phpipam_mariadb_ipam_db                 | `ipam`                                           | No                                          | phpIPAM database name |
| pdns_phpipam_mariadb_ipam_user               | `ipam`                                           | No                                          | phpIPAM database user |
| pdns_phpipam_ipam_site_title                 | `"Acme IPAM"`                                    | No                                          | phpIPAM site title |
| pdns_phpipam_ipam_site_admname               | `"Sysadmin"`                                     | No                                          | phpIPAM admin display name |
| pdns_phpipam_ipam_site_admemail              | `"admin@{{ pdns_phpipam_domain }}"`              | No                                          | phpIPAM admin email |
| pdns_phpipam_ipam_site_domain                | `"example.com"`                                  | No                                          | phpIPAM site domain |
| pdns_phpipam_ipam_site_url                   | `"http://dns.{{ pdns_phpipam_domain }}"`         | No                                          | phpIPAM site URL |
| pdns_phpipam_ipam_site_passwd_minlength      | `8`                                              | No                                          | Minimum phpIPAM password length |
| pdns_phpipam_ipam_site_passwd_maxlength      | `0`                                              | No                                          | Maximum phpIPAM password length; `0` is unlimited |
| pdns_phpipam_ipam_site_passwd_minnumbers     | `0`                                              | No                                          | Minimum digits in a phpIPAM password |
| pdns_phpipam_ipam_site_passwd_minletters     | `0`                                              | No                                          | Minimum letters in a phpIPAM password |
| pdns_phpipam_ipam_site_passwd_minlowcase     | `0`                                              | No                                          | Minimum lowercase letters in a phpIPAM password |
| pdns_phpipam_ipam_site_passwd_minupcase      | `0`                                              | No                                          | Minimum uppercase letters in a phpIPAM password |
| pdns_phpipam_ipam_site_passwd_minsymbols     | `0`                                              | No                                          | Minimum symbols in a phpIPAM password |
| pdns_phpipam_ipam_site_passwd_maxsymbols     | `0`                                              | No                                          | Maximum symbols in a phpIPAM password; `0` is unlimited |
| pdns_phpipam_ipam_site_passwd_allowedsymbols | `"#,_,-,!,[,],=,~,@"`                            | No                                          | Symbols allowed in a phpIPAM password |
| pdns_phpipam_ipam_init_api_enable            | `true`                                           | No                                          | Enable the phpIPAM API at first init |
| pdns_phpipam_ipam_init_api_string            | `""`                                             | No                                          | phpIPAM API app-id string used at init |
| pdns_phpipam_ipam_ldap_create                | `false`                                          | No                                          | Create a phpIPAM LDAP auth method at init |
| pdns_phpipam_ipam_ldap_dcs                   | `"ldap1.acme.com;ldap2.acme.com"`                | If `pdns_phpipam_ipam_ldap_create`          | LDAP servers, semicolon-separated |
| pdns_phpipam_ipam_ldap_basedn                | `"cn=users,dc=acme,dc=com"`                      | If `pdns_phpipam_ipam_ldap_create`          | LDAP base DN |
| pdns_phpipam_ipam_ldap_userdn                | `""`                                             | No                                          | LDAP user DN |
| pdns_phpipam_ipam_ldap_uidattr               | `"uid"`                                          | No                                          | LDAP username attribute |
| pdns_phpipam_ipam_ldap_security              | `"ssl"`                                          | No                                          | LDAP transport security: `ssl`, `tls`, or `none` |
| pdns_phpipam_ipam_ldap_port                  | `636`                                            | No                                          | LDAP port |
| pdns_phpipam_ipam_ldap_bindname              | `"uid=serviceaccount,cn=users,dc=acme,dc=com"`   | If `pdns_phpipam_ipam_ldap_create`          | LDAP bind DN |
| pdns_phpipam_ipam_ldap_bindpw                | `"basicpassword"`                                | If `pdns_phpipam_ipam_ldap_create`          | LDAP bind password; the default is a placeholder, override from Vault |
| pdns_phpipam_ipam_ldap_descr                 | `"blank"`                                        | No                                          | Description of the LDAP auth method |
| pdns_phpipam_galera_enabled                  | `false`                                          | No                                          | Configure the MariaDB container for Galera multi-master replication |
| pdns_phpipam_galera_cluster_name             | `"pdns_galera"`                                  | No                                          | Galera cluster name |
| pdns_phpipam_galera_cluster_address          | `""`                                             | If `pdns_phpipam_galera_enabled`            | `gcomm://` address; `gcomm://` alone bootstraps the first node, later nodes use the full member list. Set per host |
| pdns_phpipam_galera_sst_user                 | `"sst_user"`                                     | No                                          | Galera SST user |
| pdns_phpipam_galera_sst_password             | `""`                                             | If `pdns_phpipam_galera_enabled`            | Galera SST password |
| pdns_phpipam_mariadb_only                    | `false`                                          | No                                          | Deploy only the MariaDB container (Galera quorum nodes with no DNS or IPAM) |
| pdns_phpipam_mariadb_root_passwd             | `""`                                             | No                                          | MariaDB root password; empty auto-generates |
| pdns_phpipam_mariadb_pdns_passwd             | `""`                                             | No                                          | PowerDNS DB user password; empty auto-generates |
| pdns_phpipam_mariadb_ipam_passwd             | `""`                                             | No                                          | phpIPAM DB user password; empty auto-generates |
| pdns_phpipam_auth_api_key                    | `""`                                             | No                                          | PowerDNS Authoritative API key; empty auto-generates |
| pdns_phpipam_auth_web_passwd                 | `""`                                             | No                                          | PowerDNS Authoritative web password; empty auto-generates |
| pdns_phpipam_recursor_api_key                | `""`                                             | No                                          | Recursor API key; empty auto-generates |
| pdns_phpipam_dnsdist_api_key                 | `""`                                             | No                                          | dnsdist API key; empty auto-generates |
| pdns_phpipam_dnsdist_web_passwd              | `""`                                             | No                                          | dnsdist web password; empty auto-generates |
| pdns_phpipam_secrets_dir                     | `{{ playbook_dir }}/secrets/<host>/pdns_phpipam` | No                                          | Controller directory where auto-generated secrets are persisted and reused; keep it out of git |


Note: See [`mgcdrd.infrasvc.pdns_phpipam README.md`](roles/pdns_phpipam/README.md) for Galera bootstrap and full-cluster recovery


pdns_records Role Variables
--------------

Manages PowerDNS Authoritative zones and records via the PowerDNS HTTP API —
create/remove zones and create/update/remove any record type. Fully
idempotent: an unchanged re-run makes no API writes and reports no changes.

Day 2 companion to `mgcdrd.infrasvc.pdns_phpipam`, but works against any
PowerDNS Authoritative server with the API enabled.

[`mgcdrd.infrasvc.pdns_records`](roles/pdns_records/README.md)

**General role variables**

| Variable               | Default                   | Required | Description |
|------------------------|---------------------------|----------|-------------|
| pdns_records_api_url   | `"http://127.0.0.1:8081"` | No       | PowerDNS Authoritative HTTP API URL |
| pdns_records_api_key   | `""`                      | Yes      | API key for the PowerDNS server; use `{{ vault_* }}` |
| pdns_records_server_id | `"localhost"`             | No       | PowerDNS server ID; `localhost` for self-hosted instances |
| pdns_records_zones     | `[]`                      | No       | Zones to create or manage (fields below); needed when creating a new zone |
| pdns_records           | `[]`                      | No       | Records to manage (fields below) |

**pdns_records_zones[] variables**

| Field       | Required      | Description |
|-------------|---------------|-------------|
| name        | Yes           | Zone name; trailing dot added if missing. |
| kind        | No            | `Native` (default), `Master`, or `Slave`. |
| nameservers | When creating | List of NS FQDNs for a new zone. |
| state       | No            | `present` (default) or `absent`. |

**pdns_records[] variables**

| Field   | Required                    | Description |
|---------|-----------------------------|-------------|
| zone    | Yes                         | Zone the record belongs to. |
| name    | Yes                         | Record FQDN; trailing dot added if missing. |
| type    | Yes                         | `A`, `AAAA`, `CNAME`, `MX`, `TXT`, `PTR`, `NS`, `SRV`, … |
| ttl     | No                          | Seconds. Default: `300`. |
| records | Yes, unless `state: absent` | List of value strings for the RRset. MX/SRV include priority in the string, e.g. `"10 mail.example.com."`. |
| state   | No                          | `present` (default) or `absent`. |


phpipam_config Role Variables
--------------

Configures a phpIPAM instance via its REST API — customers, sections, VLANs,
nameservers, NAT policies, locations, racks, subnets, IP address
assignments, devices, and circuits — all from variables with full
idempotency. Objects reference each other by name.

Day 1 companion to `mgcdrd.infrasvc.pdns_phpipam`, run after the stack is up
to seed IPAM with the environment's structure.

[`mgcdrd.infrasvc.phpipam_config`](roles/phpipam_config/README.md)

**General role variables**

| Variable                      | Default              | Required | Description |
|-------------------------------|----------------------|----------|-------------|
| phpipam_config_url            | `"http://127.0.0.1"` | No       | phpIPAM base URL, no trailing slash |
| phpipam_config_app_id         | `"ansible"`          | No       | API application ID; must be pre-created under Administration > API |
| phpipam_config_username       | `""`                 | Yes      | phpIPAM username |
| phpipam_config_password       | `""`                 | Yes      | phpIPAM password; use `{{ vault_* }}` |
| phpipam_config_validate_certs | `true`               | No       | Validate the phpIPAM TLS certificate; set false only for a self-signed cert the controller cannot trust |
| phpipam_config_customers      | `[]`                 | No       | Customers used to tag subnets and addresses to an owner |
| phpipam_config_sections       | `[]`                 | No       | Sections, the top-level buckets that contain subnets |
| phpipam_config_vlans          | `[]`                 | No       | VLAN definitions |
| phpipam_config_nameservers    | `[]`                 | No       | Nameserver sets assignable to subnets |
| phpipam_config_nat            | `[]`                 | No       | NAT policy definitions |
| phpipam_config_locations      | `[]`                 | No       | Physical locations (data centres, rooms) |
| phpipam_config_racks          | `[]`                 | No       | Racks; reference a location by name |
| phpipam_config_subnets        | `[]`                 | No       | Subnets and their address assignments; reference a section and optionally a VLAN and nameserver by name |
| phpipam_config_devices        | `[]`                 | No       | Network devices |
| phpipam_config_circuits       | `[]`                 | No       | Network circuits and connectivity links |


Note: See [`mgcdrd.infrasvc.phpipam_config README.md`](roles/phpipam_config/README.md) for the fields of each list


postgresql Role Variables
--------------

Installs a native PostgreSQL server from the PGDG repository and manages its
listener, TLS, and host-based auth through a `conf.d` drop-in and a fully
templated `pg_hba.conf`. Optionally bootstraps roles, databases, and grants.

Built for dedicated database hosts, including unprivileged Proxmox LXC
containers where the official Postgres container is awkward.

[`mgcdrd.infrasvc.postgresql`](roles/postgresql/README.md)

**General role variables**

| Variable                            | Default           | Required                    | Description |
|-------------------------------------|-------------------|-----------------------------|-------------|
| postgresql_version                  | `"18"`            | No                          | Major PostgreSQL version |
| postgresql_manage_repo              | `true`            | No                          | Manage the PGDG repository |
| postgresql_packages_extra           | `[]`              | No                          | Extra packages installed alongside the server (names differ by OS family) |
| postgresql_listen_addresses         | `"localhost"`     | No                          | Value written to `listen_addresses` |
| postgresql_port                     | `5432`            | No                          | Listen port |
| postgresql_settings                 | `{}`              | No                          | Extra GUCs written to the managed `conf.d` drop-in as `key = 'value'` |
| postgresql_ssl                      | `false`           | No                          | Turn on server-side TLS |
| postgresql_ssl_dir                  | `""`              | No                          | Private directory the cert and key are copied into so `postgres` can read them without loosening perms on the acme tree |
| postgresql_ssl_cert_file            | `""`              | If `postgresql_ssl`         | Path to the certificate PEM |
| postgresql_ssl_key_file             | `""`              | If `postgresql_ssl`         | Path to the private key PEM |
| postgresql_ssl_ca_file              | `""`              | No                          | `ssl_ca_file` for client-certificate verification |
| postgresql_ssl_min_protocol_version | `"TLSv1.2"`       | No                          | `ssl_min_protocol_version` |
| postgresql_manage_cert              | `false`           | No                          | Issue the certificate with `mgcdrd.infrabase.acme_sh` from inside this role |
| postgresql_acme_certs               | `[]`              | If `postgresql_manage_cert` | Passed to `acme_sh_certs` |
| postgresql_hba_entries              | *(list, 3 items)* | No                          | `pg_hba.conf` is rendered entirely from this list, in order; default is local peer plus scram-sha-256 on loopback |
| postgresql_roles                    | `[]`              | No                          | Roles to create (fields below) |
| postgresql_databases                | `[]`              | No                          | Databases to create (fields below) |
| postgresql_privileges               | `[]`              | No                          | Grants passed to `community.postgresql.postgresql_privs` (fields below) |

**postgresql_roles[], postgresql_databases[], postgresql_privileges[] variables**

| List                  | Fields |
|-----------------------|-------------|
| postgresql_roles      | `name`, `password` (from `{{ vault_<name> }}`), `role_attr_flags`, `state` |
| postgresql_databases  | `name`, `owner`, `encoding`, `lc_collate`, `lc_ctype`, `template`, `state` |
| postgresql_privileges | `roles`, `database`, `privs`, `type`, `objs`, `schema`, `state` |


ups_shed Role Variables
--------------

Threshold-polling tiered shutdown for UPS events. Deploys a systemd timer
that polls `battery.charge` while the UPS is on battery and runs whichever
tier(s) it has newly crossed — k8s worker drain, then per-host `poweroff`
over SSH, then the hypervisor those hosts ran on. Credentials are read from
Vault via AppRole at run time and never written to disk.

Companion to `mgcdrd.infrasvc.nut_client`/`nut_server`; started and stopped
through `nut_client_notify_hook` on `ONBATT`/`ONLINE`.

[`mgcdrd.infrasvc.ups_shed`](roles/ups_shed/README.md)

**General role variables**

| Variable                      | Default                                  | Required | Description |
|-------------------------------|------------------------------------------|----------|-------------|
| ups_shed_ups_name             | `apc`                                    | No       | UPS name `nut_client` already monitors; polled directly with `upsc` |
| ups_shed_ups_host             | *(placeholder; set per environment)*     | Yes      | Host running upsd for that UPS |
| ups_shed_tier1_threshold      | `70`                                     | No       | Battery % at which tier 1 sheds; tiers are checked in ascending order each poll so a fast drain still runs every tier it crossed |
| ups_shed_tier2_threshold      | `40`                                     | No       | Battery % at which tier 2 sheds |
| ups_shed_tier3_threshold      | `20`                                     | No       | Battery % at which tier 3 sheds |
| ups_shed_poll_interval        | `20`                                     | No       | Seconds between battery polls once `ONBATT` fires |
| ups_shed_graceful_wait        | `30`                                     | No       | Seconds to wait after powering off a tier's guests before powering off the hypervisor |
| ups_shed_k8s_workers          | `[]`                                     | No       | Kubernetes workers drained before shedding |
| ups_shed_tier1_guests         | `[]`                                     | No       | Guests shed at tier 1, in shed order |
| ups_shed_tier1_hypervisor     | `""`                                     | No       | Hypervisor powered off after the tier 1 guests |
| ups_shed_tier2_guests         | `[]`                                     | No       | Guests shed at tier 2, in shed order |
| ups_shed_tier2_hypervisor     | `""`                                     | No       | Hypervisor powered off after the tier 2 guests |
| ups_shed_ssh_user             | `svc-ups-shutdown`                       | No       | Identity used to SSH to shed targets |
| ups_shed_ssh_key              | `/root/.ssh/id_ed25519_svc-ups-shutdown` | No       | Private key for that identity |
| ups_shed_vault_addr           | `"{{ vault_addr }}"`                     | No       | Vault address; comes from `inventory-common`'s `vault_addr` |
| ups_shed_vault_role_id_file   | `/etc/vault/ups-shutdown-role-id`        | No       | AppRole role_id file, pre-positioned on the host |
| ups_shed_vault_secret_id_file | `/etc/vault/ups-shutdown-secret-id`      | No       | AppRole secret_id file, pre-positioned on the host |
| ups_shed_vault_secret_path    | *(see defaults)*                         | No       | Vault KV v2 API path holding the shed credentials, including `k8s_drain_token` |
| ups_shed_k8s_api              | *(placeholder; set per environment)*     | No       | Kubernetes API URL used to drain workers |
| ups_shed_ansible_dir          | `/opt/ups-shed`                          | No       | Working directory on the responder host |
| ups_shed_state_dir            | `/var/lib/ups-shed`                      | No       | State directory on the responder host |
| ups_shed_log_file             | `/var/log/ups-shed.log`                  | No       | Log file on the responder host |


vsftp Role Variables
--------------

Installs and configures vsftpd. Generates a fully managed `/etc/vsftpd.conf`
from variables covering every vsftpd option.

Beyond the role-level variables below, every vsftpd directive is exposed as
`vsftp_<directive>` (e.g. `vsftp_listen`, `vsftp_pasv_enable`,
`vsftp_pasv_min_port`). Unset ones fall back to vsftpd's own default; the
full annotated list is commented in `roles/vsftp/vars/main.yml`.

[`mgcdrd.infrasvc.vsftp`](roles/vsftp/README.md)

**General role variables**

| Variable                          | Default            | Required | Description |
|-----------------------------------|--------------------|----------|-------------|
| vsftp_show_comments               | `false`            | No       | Include inline comments in the generated `/etc/vsftpd.conf` |
| vsftp_background                  | `"NO"`             | No       | `background`: `NO` lets systemd manage the process (normal case), `YES` daemonizes |
| vsftp_selinux_register_pasv_ports | `true`             | No       | RedHat only: register the passive port range as `ftp_port_t`; no-op when PASV is off |
| vsftp_selinux_ftpd_full_access    | `false`            | No       | RedHat only: set the `ftpd_full_access` SELinux boolean, needed when home directories sit outside the expected FTP paths |
| vsftp_\<directive\>               | *(vsftpd default)* | No       | Any vsftpd.conf directive; see `vars/main.yml` |


Note: See [`mgcdrd.infrasvc.vsftp README.md`](roles/vsftp/README.md) for the directives grouped by area (local users, passive mode, SSL/TLS, logging)

