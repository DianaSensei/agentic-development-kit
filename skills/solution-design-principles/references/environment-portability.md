# Environment Portability: Designing for VM and Cloud Together

Principles for building a system so that *where* it runs - a self-managed VM, a managed cloud service,
or both at once (hybrid) - is a deployment-time decision, not a design-time assumption baked into the
code. This is the design counterpart to `architecture-designer/references/deployment-topology.md`:
that reference decides *which* topology to run on; this one keeps the code from being locked into that
choice once made, and keeps a VM-cloud boundary from becoming a hidden source of bugs.

Portability is not free - it costs abstraction, and abstraction has a maintenance cost. Apply these
principles proportionate to the actual likelihood of needing to move or split across environments, per
YAGNI (see `code-design-heuristics.md`). A system with a firm, permanent, single-topology decision does
not need to pay this cost preemptively.

## 1. Separate Configuration from Code, Fully

This is 12-Factor's Config principle (`twelve-factor-app.md`, factor III) applied specifically to the
VM/cloud boundary: every value that differs between "running on a VM" and "running on managed cloud" -
hostnames, credentials, storage paths, queue endpoints - must come from environment configuration, never
from a code branch that checks "am I on a VM or in the cloud."

**Symptom of violation**: `if (process.env.PLATFORM === "vm") { ... } else { ... }` scattered through
business logic.

**Fix**: The business logic calls an abstraction (`StorageService.save(...)`); which concrete
implementation that resolves to (local disk on a VM, S3/Blob Storage in the cloud) is decided once, at
the composition root, from config - see principle 3 below.

## 2. Package for the Runtime, Not the Environment

A container image (OCI/Docker) that runs identically under a container runtime on a VM (`docker run`,
`containerd`) and under a managed cloud container service (ECS, Cloud Run, AKS/EKS/GKE) removes an entire
class of "works on cloud, breaks on VM" bugs, because the artifact that runs is byte-for-byte identical -
only the orchestrator around it changes.

**Practice**: Build one artifact; deploy it to whichever topology is chosen. Avoid environment-specific
build steps (a "cloud build" vs. a "VM build") - if the build must differ, the portability has already
been lost at the build stage, before deployment even enters the picture.

**Where this doesn't apply**: A component intentionally using a topology-specific managed service with no
practical VM equivalent (e.g. a fully managed serverless function tied to a specific event source) is not
a portability failure - it's a deliberate, documented trade-off (see principle 5). Don't force portability
onto a component that was never meant to have it.

## 3. Isolate Environment-Specific Integration Behind Ports & Adapters

Apply the Hexagonal Architecture (Ports & Adapters) pattern at exactly the seams where the system talks
to something that differs between VM and cloud: object storage, message queues, secrets, identity. Define
a small interface (the port) that expresses what the business logic needs; write one adapter per
environment.

```
// Port - what the business logic needs, independent of environment
interface ObjectStore {
  put(key: string, data: bytes): void
  get(key: string): bytes
}

// Adapter for VM topology
class LocalDiskObjectStore implements ObjectStore { ... }

// Adapter for cloud topology
class S3ObjectStore implements ObjectStore { ... }
```

**Why this is the load-bearing pattern for portability**: it turns "move this component from VM to
cloud" from a business-logic rewrite into an adapter swap plus a config change - the risk and cost of a
topology change collapses to the adapter, which is small and directly testable in isolation.

**Where NOT to apply this**: Don't wrap every dependency behind a port "just in case" - this is DIP/OCP
applied without a real driver (see `solid-principles.md` on over-applying DIP). Apply it specifically at
the boundaries identified in `deployment-topology.md`'s hybrid design requirements (storage, messaging,
identity, observability sinks) - the seams that concretely differ by topology, not every dependency in
the system.

## 4. One Identity and Secrets Model, Regardless of Where a Service Runs

A hybrid system with cloud-native IAM roles on one side and static API keys checked into VM config on the
other has two different security postures to audit, reason about, and eventually get wrong. Use one
consistent model - most commonly mutual TLS between services plus a single identity provider/secret
store reachable from both environments - so a service's identity and its access rights don't depend on
which side of the VM-cloud boundary it happens to run on.

**Symptom of violation**: A credential rotation runbook that has a different procedure "if it's the VM
service" vs. "if it's the cloud service."

## 5. Name the Portability Trade-off Explicitly, Don't Assume It's Free

Full portability - the ability to move any component to any topology at will - is not a goal in itself,
because avoiding every provider-specific capability also means giving up the managed-service benefits
that made cloud-native worth choosing in the first place (see `architecture-designer`'s
`deployment-topology.md` on Cloud-Native trade-offs). For each component, state explicitly:

- **Fully portable** - built to the ports & adapters pattern above; can move between VM and cloud with an
  adapter swap and config change. Reserve this for components with a real, near-term reason to move
  (declared migration plan, data-residency flexibility requirement).
- **Deliberately coupled** - intentionally uses a topology-specific capability (a managed queue's
  exactly-once semantics, a serverless platform's event triggers) because the benefit outweighs the
  lock-in, and moving it is accepted as a rewrite if it ever comes to that.

Recording this per component (in the same ADR that documents the topology decision - see
`architecture-designer`'s `adr-template.md`) prevents two failure modes: over-engineering portability
into a component that will never move, and discovering - only when a migration is actually needed - that
a "surely portable" component was quietly cloud-coupled all along.

## 6. Observability and Operational Behavior Must Match Across the Boundary

A component behaves identically from an operations standpoint regardless of topology: logs go to the
same aggregation pipeline (12-Factor's Logs, factor XI), health checks respond the same way, graceful
shutdown on `SIGTERM` works the same way (12-Factor's Disposability, factor IX - see
`twelve-factor-app.md`). If the VM-hosted half of a hybrid system is invisible to the same dashboards,
alerts, and traces as the cloud-hosted half, the team is now operating two systems that happen to share a
name, not one system.

## Applying This Skill Alongside `deployment-topology.md`

Typical sequence when a system spans VM and cloud:
1. `architecture-designer` decides the topology per component (VM, cloud-native, or a deliberate hybrid
   split) and the driver behind each choice.
2. This reference is applied to each component classified **Fully portable** above - identify its
   environment-specific seams, define ports, write adapters, verify config-only environment switching.
3. Components classified **Deliberately coupled** skip steps requiring portability, but still get
   principle 4 (consistent identity) and principle 6 (consistent observability) - those apply regardless
   of whether a component is meant to move.
