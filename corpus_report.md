# E0.5d Spec-Shape Conformance Corpus Report

## Aggregated Reasons for Dropped Endpoints
| Reason | Count |
|---|---|
| happy-path probe is skipped on templated paths — a sampled value would address a resource that need not exist, and its 404 would read as a divergence. Covering it needs a known-good identifier | 1178 |
| no probe for POST: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither | 640 |
| no probe for DELETE: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither | 425 |
| path parameters could not be sampled ({namespace}, {name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 203 |
| no probe for PUT: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither | 173 |
| no probe for PATCH: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither | 152 |
| no mechanical hypothesis was derivable from the documented responses, request body, or parameters | 149 |
| path parameters could not be sampled ({namespace}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 141 |
| path parameters could not be sampled ({database_cluster_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 41 |
| path parameters could not be sampled ({uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 22 |
| path parameters could not be sampled ({cluster_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 16 |
| path parameters could not be sampled ({droplet_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 15 |
| path parameters could not be sampled ({id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 14 |
| path parameters could not be sampled ({app_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 14 |
| path parameters could not be sampled ({registry_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 12 |
| path parameters could not be sampled ({firewall_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 9 |
| path parameters could not be sampled ({image_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 9 |
| path parameters could not be sampled ({api_key_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 9 |
| path parameters could not be sampled ({lb_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 8 |
| happy-path probe is skipped when query parameters are required (query) — no value can be assumed safe | 7 |
| path parameters could not be sampled ({dedicated_inference_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 7 |
| path parameters could not be sampled ({pa_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 7 |
| path parameters could not be sampled ({vpc_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 7 |
| path parameters could not be sampled ({autoscale_pool_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 6 |
| path parameters could not be sampled ({namespace_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 6 |
| path parameters could not be sampled ({project_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 6 |
| path parameters could not be sampled ({volume_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 6 |
| path parameters could not be sampled ({check_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 6 |
| path parameters could not be sampled ({workspace_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 6 |
| no probe for HEAD: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither | 6 |
| path parameters could not be sampled ({registry_name}, {repository_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 5 |
| path parameters could not be sampled ({agent_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 5 |
| path parameters could not be sampled ({eval_run_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 5 |
| path parameters could not be sampled ({resource_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 4 |
| path parameters could not be sampled ({cdn_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 4 |
| path parameters could not be sampled ({invoice_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 4 |
| path parameters could not be sampled ({database_cluster_uuid}, {username}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 4 |
| path parameters could not be sampled ({database_cluster_uuid}, {subject_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 4 |
| path parameters could not be sampled ({domain_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 4 |
| path parameters could not be sampled ({domain_name}, {domain_record_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 4 |
| path parameters could not be sampled ({floating_ip}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 4 |
| path parameters could not be sampled ({cluster_id}, {node_pool_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 4 |
| path parameters could not be sampled ({reserved_ip}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 4 |
| path parameters could not be sampled ({byoip_prefix_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 4 |
| path parameters could not be sampled ({snapshot_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 4 |
| path parameters could not be sampled ({access_key}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 4 |
| path parameters could not be sampled ({tag_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 4 |
| path parameters could not be sampled ({knowledge_base_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 4 |
| path parameters could not be sampled ({ssh_key_identifier}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({app_id}, {deployment_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({app_id}, {event_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({database_cluster_uuid}, {replica_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({database_cluster_uuid}, {pool_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({database_cluster_uuid}, {topic_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({database_cluster_uuid}, {logsink_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({namespace_id}, {trigger_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({alert_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({destination_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({nfs_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({reserved_ipv6}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({vpc_peering_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({check_id}, {alert_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({agent_uuid}, {api_key_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({parent_agent_uuid}, {child_agent_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({batch_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 3 |
| path parameters could not be sampled ({app_id}, {component_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({app_id}, {deployment_id}, {component_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({app_id}, {job_invocation_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({certificate_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({database_cluster_uuid}, {database_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({namespace_id}, {key_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({sink_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({nfs_snapshot_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({share_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({access_point_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({registry_name}, {garbage_collection_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({registry_name}, {repository_name}, {repository_tag}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({registry_name}, {repository_name}, {manifest_digest}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({id}, {backup_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({agent_uuid}, {function_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({agent_uuid}, {knowledge_base_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({dataset_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({metric_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({evaluation_run_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({test_case_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({indexing_job_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({knowledge_base_uuid}, {data_source_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| path parameters could not be sampled ({eval_preset_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 2 |
| happy-path probe is skipped when query parameters are required (scope) — no value can be assumed safe | 1 |
| happy-path probe is skipped when query parameters are required (name, scope) — no value can be assumed safe | 1 |
| happy-path probe is skipped when query parameters are required (filter) — no value can be assumed safe | 1 |
| happy-path probe is skipped when query parameters are required (customer) — no value can be assumed safe | 1 |
| happy-path probe is skipped when query parameters are required (account) — no value can be assumed safe | 1 |
| happy-path probe is skipped when query parameters are required (payment_record) — no value can be assumed safe | 1 |
| happy-path probe is skipped when query parameters are required (value_list) — no value can be assumed safe | 1 |
| happy-path probe is skipped when query parameters are required (setup_intent) — no value can be assumed safe | 1 |
| happy-path probe is skipped when query parameters are required (subscription) — no value can be assumed safe | 1 |
| happy-path probe is skipped when query parameters are required (payment_intent) — no value can be assumed safe | 1 |
| happy-path probe is skipped when query parameters are required (q) — no value can be assumed safe | 1 |
| path parameters could not be sampled ({action_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({app_slug}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({app_id}, {job_name}, {job_invocation_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({slug}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({app_id}, {alert_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({account_urn}, {start_date}, {end_date}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({database_cluster_uuid}, {migration_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({database_cluster_uuid}, {subject_name}, {version}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({database_cluster_uuid}, {index_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({dedicated_inference_id}, {accelerator_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({dedicated_inference_id}, {token_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({droplet_id}, {action_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({floating_ip}, {action_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({image_id}, {action_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({cluster_id}, {node_pool_id}, {node_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({reserved_ip}, {action_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({scan_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({scan_id}, {finding_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({suppression_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({volume_id}, {action_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({vpc_id}, {vpc_peering_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({agent_uuid}, {guardrail_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({evaluation_run_uuid}, {prompt_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |
| path parameters could not be sampled ({evaluation_test_case_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema | 1 |

## Per-API Breakdown
### Stripe
- Total Operations: 589
- Probes Planned: 95
- Endpoints Dropped: 494
- **Drop Reasons:**
  - 294: no probe for POST: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 32: no probe for DELETE: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 151: happy-path probe is skipped on templated paths — a sampled value would address a resource that need not exist, and its 404 would read as a divergence. Covering it needs a known-good identifier
  - 1: happy-path probe is skipped when query parameters are required (scope) — no value can be assumed safe
  - 1: happy-path probe is skipped when query parameters are required (name, scope) — no value can be assumed safe
  - 1: happy-path probe is skipped when query parameters are required (filter) — no value can be assumed safe
  - 7: happy-path probe is skipped when query parameters are required (query) — no value can be assumed safe
  - 1: happy-path probe is skipped when query parameters are required (customer) — no value can be assumed safe
  - 1: happy-path probe is skipped when query parameters are required (account) — no value can be assumed safe
  - 1: happy-path probe is skipped when query parameters are required (payment_record) — no value can be assumed safe
  - 1: happy-path probe is skipped when query parameters are required (value_list) — no value can be assumed safe
  - 1: happy-path probe is skipped when query parameters are required (setup_intent) — no value can be assumed safe
  - 1: happy-path probe is skipped when query parameters are required (subscription) — no value can be assumed safe
  - 1: happy-path probe is skipped when query parameters are required (payment_intent) — no value can be assumed safe

### GitHub
- Total Operations: 1216
- Probes Planned: 362
- Endpoints Dropped: 854
- **Drop Reasons:**
  - 484: happy-path probe is skipped on templated paths — a sampled value would address a resource that need not exist, and its 404 would read as a divergence. Covering it needs a known-good identifier
  - 67: no probe for POST: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 48: no probe for PATCH: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 179: no probe for DELETE: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 75: no probe for PUT: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 1: happy-path probe is skipped when query parameters are required (q) — no value can be assumed safe

### OpenAI
- Total Operations: 288
- Probes Planned: 133
- Endpoints Dropped: 155
- **Drop Reasons:**
  - 60: happy-path probe is skipped on templated paths — a sampled value would address a resource that need not exist, and its 404 would read as a divergence. Covering it needs a known-good identifier
  - 52: no probe for POST: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 43: no probe for DELETE: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither

### Slack
**Error loading/parsing:** Failed to load
### Discord
- Total Operations: 242
- Probes Planned: 37
- Endpoints Dropped: 205
- **Drop Reasons:**
  - 32: no probe for PATCH: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 90: happy-path probe is skipped on templated paths — a sampled value would address a resource that need not exist, and its 404 would read as a divergence. Covering it needs a known-good identifier
  - 22: no probe for POST: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 22: no probe for PUT: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 39: no probe for DELETE: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither

### DigitalOcean
- Total Operations: 659
- Probes Planned: 0
- Endpoints Dropped: 659
- **Drop Reasons:**
  - 148: no mechanical hypothesis was derivable from the documented responses, request body, or parameters
  - 79: no probe for POST: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 3: path parameters could not be sampled ({ssh_key_identifier}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({action_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({app_slug}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 4: path parameters could not be sampled ({resource_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 14: path parameters could not be sampled ({id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 14: path parameters could not be sampled ({app_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({app_id}, {component_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 3: path parameters could not be sampled ({app_id}, {deployment_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({app_id}, {deployment_id}, {component_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({app_id}, {job_invocation_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({app_id}, {job_name}, {job_invocation_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 3: path parameters could not be sampled ({app_id}, {event_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({slug}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({app_id}, {alert_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 4: path parameters could not be sampled ({cdn_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({certificate_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 4: path parameters could not be sampled ({invoice_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({account_urn}, {start_date}, {end_date}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 41: path parameters could not be sampled ({database_cluster_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({database_cluster_uuid}, {migration_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 3: path parameters could not be sampled ({database_cluster_uuid}, {replica_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 4: path parameters could not be sampled ({database_cluster_uuid}, {username}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({database_cluster_uuid}, {database_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 3: path parameters could not be sampled ({database_cluster_uuid}, {pool_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 3: path parameters could not be sampled ({database_cluster_uuid}, {topic_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 3: path parameters could not be sampled ({database_cluster_uuid}, {logsink_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 4: path parameters could not be sampled ({database_cluster_uuid}, {subject_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({database_cluster_uuid}, {subject_name}, {version}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 4: no probe for PUT: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 1: path parameters could not be sampled ({database_cluster_uuid}, {index_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 7: path parameters could not be sampled ({dedicated_inference_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({dedicated_inference_id}, {accelerator_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({dedicated_inference_id}, {token_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 4: path parameters could not be sampled ({domain_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 4: path parameters could not be sampled ({domain_name}, {domain_record_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 5: no probe for DELETE: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 15: path parameters could not be sampled ({droplet_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({droplet_id}, {action_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 6: path parameters could not be sampled ({autoscale_pool_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 9: path parameters could not be sampled ({firewall_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 4: path parameters could not be sampled ({floating_ip}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({floating_ip}, {action_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 6: path parameters could not be sampled ({namespace_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 3: path parameters could not be sampled ({namespace_id}, {trigger_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({namespace_id}, {key_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 9: path parameters could not be sampled ({image_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({image_id}, {action_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 16: path parameters could not be sampled ({cluster_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 4: path parameters could not be sampled ({cluster_id}, {node_pool_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({cluster_id}, {node_pool_id}, {node_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 8: path parameters could not be sampled ({lb_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 3: path parameters could not be sampled ({alert_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 3: path parameters could not be sampled ({destination_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({sink_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 3: path parameters could not be sampled ({nfs_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({nfs_snapshot_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({share_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({access_point_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 7: path parameters could not be sampled ({pa_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: no probe for PATCH: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 6: path parameters could not be sampled ({project_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 12: path parameters could not be sampled ({registry_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({registry_name}, {garbage_collection_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 5: path parameters could not be sampled ({registry_name}, {repository_name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({registry_name}, {repository_name}, {repository_tag}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({registry_name}, {repository_name}, {manifest_digest}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 4: path parameters could not be sampled ({reserved_ip}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({reserved_ip}, {action_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 3: path parameters could not be sampled ({reserved_ipv6}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 4: path parameters could not be sampled ({byoip_prefix_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({scan_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({scan_id}, {finding_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({suppression_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 4: path parameters could not be sampled ({snapshot_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 4: path parameters could not be sampled ({access_key}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 4: path parameters could not be sampled ({tag_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({id}, {backup_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 6: path parameters could not be sampled ({volume_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({volume_id}, {action_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 7: path parameters could not be sampled ({vpc_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({vpc_id}, {vpc_peering_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 3: path parameters could not be sampled ({vpc_peering_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 6: path parameters could not be sampled ({check_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 3: path parameters could not be sampled ({check_id}, {alert_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 5: path parameters could not be sampled ({agent_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 3: path parameters could not be sampled ({agent_uuid}, {api_key_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({agent_uuid}, {function_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({agent_uuid}, {guardrail_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({agent_uuid}, {knowledge_base_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 3: path parameters could not be sampled ({parent_agent_uuid}, {child_agent_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 22: path parameters could not be sampled ({uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 9: path parameters could not be sampled ({api_key_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({dataset_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({metric_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({evaluation_run_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({evaluation_run_uuid}, {prompt_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 1: path parameters could not be sampled ({evaluation_test_case_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({test_case_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({indexing_job_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 4: path parameters could not be sampled ({knowledge_base_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({knowledge_base_uuid}, {data_source_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 2: path parameters could not be sampled ({eval_preset_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 5: path parameters could not be sampled ({eval_run_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 6: path parameters could not be sampled ({workspace_uuid}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 3: path parameters could not be sampled ({batch_id}) — declare them under the operation's or the PathItem's `parameters` with a typed schema

### GitLab
**Error loading/parsing:** Failed to load
### Petstore
**Error loading/parsing:** Failed to load
### Twilio
- Total Operations: 197
- Probes Planned: 4
- Endpoints Dropped: 193
- **Drop Reasons:**
  - 62: no probe for POST: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 99: happy-path probe is skipped on templated paths — a sampled value would address a resource that need not exist, and its 404 would read as a divergence. Covering it needs a known-good identifier
  - 32: no probe for DELETE: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither

### Kubernetes
- Total Operations: 1190
- Probes Planned: 249
- Endpoints Dropped: 947
- **Drop Reasons:**
  - 294: happy-path probe is skipped on templated paths — a sampled value would address a resource that need not exist, and its 404 would read as a divergence. Covering it needs a known-good identifier
  - 64: no probe for POST: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 141: path parameters could not be sampled ({namespace}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 203: path parameters could not be sampled ({namespace}, {name}) — declare them under the operation's or the PathItem's `parameters` with a typed schema
  - 95: no probe for DELETE: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 6: no probe for HEAD: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 71: no probe for PATCH: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 72: no probe for PUT: a happy-path probe is GET-only, since sending sampled data would mutate state. Mutation probes need a required request-body field or an enum to violate, and this operation documents neither
  - 1: no mechanical hypothesis was derivable from the documented responses, request body, or parameters

