# Deployment Topology: VM, Cloud-Native, Hybrid, Multi-Cloud

Where a system's *application architecture pattern* (monolith/microservices/serverless/event-driven, see
`architecture-patterns.md`) answers "how is the software structured," deployment topology answers "what
infrastructure does it run on and who manages that infrastructure." These are two independent axes - a
microservices system can run entirely on self-managed VMs, and a monolith can run on a fully managed
cloud platform. Decide both explicitly; don't let one imply the other.

## The Four Topologies

| Topology | Who manages the infra | Typical driver |
| --- | --- | --- |
| **VM / IaaS (on-prem or cloud VMs)** | You - OS, patching, scaling, networking | Full control, existing investment, compliance/data-residency, predictable steady-state load |
| **Cloud-Native (PaaS/serverless/managed)** | The provider - you manage code/config only | Speed of delivery, variable load, minimal ops team, willingness to accept vendor coupling |
| **Hybrid (VM + Cloud together)** | Split - some workloads self-managed, some managed | Gradual migration, data that legally/technically can't leave a given environment, latency-sensitive components near the data source |
| **Multi-Cloud (2+ cloud providers)** | Multiple providers | Regulatory requirement, negotiating leverage, avoiding single-provider outage risk - rarely worth the operational cost otherwise |

## VM / IaaS

**When to use**: Predictable, steady-state load where autoscaling adds cost without benefit; regulatory
or data-residency requirements that mandate specific physical control; an existing investment
(licensed software, specialized hardware, established ops tooling) that a lift-to-managed-service
migration doesn't justify yet; a team with strong ops/infra skills who would rather own the trade-off
than pay a managed-service premium.

**Pros**: Full control over the runtime and network; predictable cost at steady load; no forced API
coupling to a provider's proprietary services.

**Cons**: You own patching, scaling, and failover - every hour of that is an hour not spent on the
product; slower to scale out (provisioning a new VM is not instant); high-availability requires you to
build the redundancy the cloud would otherwise provide by default.

**Common mistake**: Choosing VM/IaaS purely out of familiarity when the actual load pattern is bursty -
this is where autoscaling cloud-native infra earns back its premium quickly.

## Cloud-Native (PaaS / Serverless / Managed Services)

**When to use**: Variable or unpredictable load where autoscaling saves real cost; a small team that
cannot afford a dedicated ops function; a need to ship fast with managed reliability (managed databases,
managed queues, managed load balancing) instead of building it.

**Pros**: Elastic scaling handled by the provider; reduced operational burden; faster time-to-production
for standard workloads.

**Cons**: Provider coupling - proprietary APIs/services make switching providers expensive; cost can
become unpredictable or high at sustained high load compared to reserved VM capacity; less control over
the exact runtime environment (patch timing, kernel-level tuning).

**Common mistake**: Assuming "cloud-native" is free of the Reliability/Performance pillars' work - a
managed service still needs a resilience and observability design (see `resilience-patterns.md`,
`distributed-observability.md`), the provider only removes the undifferentiated infrastructure toil, not
the architectural responsibility.

## Hybrid (VM + Cloud, Deliberately Combined)

**Definition**: Some components run on self-managed VMs (on-prem or IaaS), others on managed cloud
services, with the two communicating as part of one system - not a temporary migration state, but a
deliberate, ongoing split.

**When to use**:
- A legacy system on VMs that isn't worth migrating, with new capability built cloud-native and
  integrated via a defined API boundary (the common shape during incremental modernization - see
  `legacy-modernizer` for the migration path itself).
- Data-residency or latency requirements that pin specific data/processing to a specific physical
  location (on-prem or a specific region), while less-constrained workloads run cloud-native.
- Cost arbitrage: steady-state, predictable-load components stay on reserved VM capacity; bursty
  components run cloud-native to avoid over-provisioning VMs for a peak that's rare.

**Design requirements specific to hybrid** (raise every one explicitly, don't let them default):
1. **Connectivity** - how do the VM side and cloud side reach each other: VPN, a dedicated interconnect
   (e.g. AWS Direct Connect / Azure ExpressRoute), or public internet with mTLS? Latency and reliability
   of this link becomes a first-class dependency for every cross-boundary call.
2. **Identity and secrets** - a single, consistent auth model across both environments (e.g. mTLS between
   services, a shared identity provider) - not "cloud IAM on one side, a static API key on the other."
3. **Network addressing** - private IP ranges must not collide between the VM network and the cloud
   VPC/VNet if they're peered.
4. **Observability parity** - logs/metrics/traces from both sides correlate into one place (see
   `distributed-observability.md`); a hybrid system where the VM side is a blind spot to the cloud side's
   tracing defeats the point of correlation.
5. **Failure domain isolation** - an outage of the connectivity link between VM and cloud is now a
   distinct failure mode that needs its own mitigation (see `resilience-patterns.md`), not an edge case.

**Cons**: The operational cost of *both* topologies simultaneously - you don't get to skip VM ops, and
you still take on cloud coupling. Justify hybrid by a concrete driver above, not by indecision between
the other two.

## Multi-Cloud (2+ Cloud Providers)

**When to use**: A genuine regulatory requirement for provider diversity; contractual/negotiating
leverage at a scale where it materially affects pricing; a specific, unmovable service only available on
a second provider. Rarely justified purely for "avoiding lock-in" in the abstract - the operational
complexity of running two providers' worth of tooling, IAM, and networking is usually a larger risk than
the lock-in it avoids.

**Cons**: Doubles the surface area for security, networking, and observability configuration; forces the
team to either learn two providers deeply or use only the lowest-common-denominator features of each,
losing the managed-service benefit that made cloud-native attractive in the first place.

**Common mistake**: Choosing multi-cloud as a default risk-mitigation strategy without a concrete trigger
- this is almost always over-engineering relative to the actual risk (see `solution-design-principles`
for the general principle of not building for hypothetical requirements).

## Decision Checklist

Answer explicitly, don't default silently to "whatever we used last time":

1. Is the load pattern steady-state or bursty/unpredictable? → steady favors VM, bursty favors
   cloud-native.
2. Is there a hard data-residency, compliance, or latency-to-source constraint pinning any component to
   a specific physical location? → that component may need VM/on-prem or hybrid regardless of the rest.
3. Does the team have the ops capacity to own VM-level infrastructure, or is that capacity better spent
   on the product? → thin ops capacity favors cloud-native.
4. Is there an existing VM/on-prem investment (licensing, hardware, established runbooks) that isn't yet
   worth migrating? → hybrid, with a stated trigger for when to revisit.
5. Is there a concrete, named driver (not a hypothetical) for spanning more than one cloud provider? → if
   no, stay single-provider.

Document the answer as an ADR (see `adr-template.md`) - this decision has significant, hard-to-reverse
cost implications and belongs on the record like any other significant architectural decision.

## Boundary

This file decides *which topology* a system or component runs on. It does not cover how to design the
system's code so that a topology decision doesn't lock it in (config abstraction, containerization,
avoiding proprietary-API coupling in business logic, ports & adapters) - that's
`solution-design-principles`'s `references/environment-portability.md`. Use both together when a system
must remain portable across VM and cloud, or is expected to migrate between them.
