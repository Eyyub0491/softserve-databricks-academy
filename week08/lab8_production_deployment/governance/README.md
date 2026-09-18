# Governance and Permissions

This directory documents the Gold-layer governance model used in Lab 6 and the way it should be carried into Lab 8.

## Reference policy

The original Lab 6 design includes:

- A row filter on `dim_customers.state` using `filter_customers_by_state(state STRING)`.
- Allowed states: `CA`, `NY`, and `TX`.
- A mask on `tax_id` using `mask_tax_id(value STRING)`.
- Default visibility where `admins` see the original value and other users see `REDACTED`.
- Schema-level access for `USE SCHEMA` and `SELECT` for the `account users` group.

The Lab 6 examples used the `lab5.gold` namespace as a concrete reference. Lab 8 keeps the governance concept but parameterizes the namespace through bundle variables instead of hard-coding a single workspace name.

## Local status

The bundle stores the governance model as documentation and configuration references, but it does not create workspace-specific grants in this repository. Actual users, groups, service principals, and ownership assignments must be confirmed separately for each target workspace before deployment.

## What is safe to represent in source control

- Governance function definitions and policy logic.
- Column-level enforcement targets.
- Target-specific catalog and schema references.
- The schema and bundle structure in `resources/schemas.yml`.

## What must be resolved in the target workspace

- Group names and IDs.
- Service principals and owners.
- Dashboard, pipeline, and job principals.
- Final `dev` and `prod` permission grants.

The local repository keeps this information explicit without pretending the target workspace identities are known or available.
