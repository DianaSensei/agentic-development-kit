# Code Design Heuristics

Principles below the class/interface level — how to shape logic, module boundaries, and dependencies day
to day. Unlike SOLID, several of these are explicitly heuristics, not laws: they trade off against each
other, and knowing when *not* to apply one is as important as applying it.

## DRY — Don't Repeat Yourself

**Definition**: Every piece of knowledge should have a single, unambiguous, authoritative representation
in the system.

**Symptom of violation**: The same business rule (a tax rate, a validation regex, a pricing formula)
is copy-pasted in multiple places; fixing a bug requires finding and patching every copy.

**Fix**: Extract the rule to one place; everything else calls it.

**Critical caution — duplication vs. the wrong abstraction**: DRY is about *knowledge*, not *code that
looks similar*. Two pieces of code that are textually similar today but represent different business
rules that will evolve independently are not a DRY violation — merging them creates a false coupling
that breaks the moment one rule changes and the other doesn't. When in doubt: "duplication is far
cheaper than the wrong abstraction" (Sandi Metz). Prefer to wait for a third occurrence before
abstracting (rule of three), unless the duplicated logic is a single well-understood invariant (e.g. a
formula, a regex) that is *obviously* one piece of knowledge from the start.

## KISS — Keep It Simple

**Definition**: Prefer the simplest design that correctly solves the actual problem; complexity must be
justified by a real requirement, not by anticipated cleverness.

**Symptom of violation**: A solution uses a design pattern, framework feature, or abstraction layer that
a reader has to research before understanding what 5 lines of straightforward code would have shown
directly.

**Fix**: Ask "what is the simplest thing that could work here, given the actual (not imagined)
requirements?" and default to it. Add complexity only when a concrete, current requirement demands it.

**When it conflicts with DRY/OCP**: KISS sometimes argues *against* an abstraction that DRY or OCP would
suggest. When two occurrences of logic are simple and the abstraction would be more complex than the
duplication it removes, KISS wins — don't abstract for abstraction's sake.

## YAGNI — You Aren't Gonna Need It

**Definition**: Don't build capability for a requirement that doesn't exist yet, no matter how likely it
seems.

**Symptom of violation**: Configuration options, extension points, or abstraction layers exist with
exactly one implementation/value, "in case we need to support X later."

**Fix**: Build for the requirements that exist now. When the second real requirement actually shows up,
refactor — it's usually cheaper than the carrying cost of unused flexibility, and by then you know the
*actual* shape of the variation instead of guessing it.

**Where YAGNI does not apply**: Requirements explicitly stated as near-term (an NFR, a known roadmap
item within the current milestone) are not "hypothetical" — YAGNI targets *speculative* generality, not
documented near-term scope.

## Coupling and Cohesion

**Coupling** — how much one module knows about / depends on another's internals. **Cohesion** — how
closely the responsibilities within one module relate to each other. The goal: **high cohesion, low
coupling** — modules that are internally focused and externally independent.

| | Low Cohesion | High Cohesion |
| --- | --- | --- |
| **High Coupling** | Worst — tangled *and* unfocused | Common but limiting — focused units, still tightly wired together |
| **Low Coupling** | Fragile — independent but each module does unrelated things | Best — focused units, changeable independently |

**Symptom of tight coupling**: Changing module A's internal implementation (not its public contract)
breaks module B's tests.

**Symptom of low cohesion**: A module's methods each operate on a different, non-overlapping subset of
its own fields — a sign it's really several modules wearing one name.

**Fix for coupling**: Depend on the smallest interface that satisfies the need (see DIP, ISP); pass data,
not the object that produced it, when only the data is needed.

**Fix for cohesion**: Group by what changes together and what data is actually shared, not by technical
layer alone (e.g. not just "all validators in one file" if they validate unrelated domains).

## Law of Demeter (Principle of Least Knowledge)

**Definition**: A method should only talk to its immediate collaborators — not reach through one object
to get to another ("don't talk to strangers").

**Symptom of violation**: A chain like `order.getCustomer().getAddress().getCity()` — the caller now
depends on the internal structure of `Customer` and `Address`, not just `Order`.

```
// Violates LoD — caller depends on 3 levels of internal structure
city = order.getCustomer().getAddress().getCity();

// Follows LoD — Order exposes what callers need
city = order.getShippingCity();
```

**Concrete failure mode this prevents**: A refactor of `Address`'s internal structure breaking dozens of
unrelated call sites across the codebase that only wanted the city.

**When NOT to over-apply**: Fluent builders and simple data-transfer chains (`list.stream().map(...)`)
are not Law of Demeter violations — the rule targets chains that traverse *domain object* internals to
reach unrelated behavior, not standard library composition.

## Composition Over Inheritance

**Definition**: Prefer assembling behavior from small, composable parts (has-a) over building deep class
hierarchies (is-a), unless the relationship is a genuine, stable "is-a" that satisfies LSP.

**Symptom of violation**: A class hierarchy more than 2-3 levels deep, or a base class with methods that
only some subclasses actually use meaningfully (frequently also an LSP violation).

**Fix**: Extract the varying behavior into an injected strategy/collaborator instead of a subclass.

```
// Inheritance — brittle as behaviors combine
class Duck extends Animal { fly() {...} swim() {...} quack() {...} }
class RubberDuck extends Duck { fly() { throw ... } } // forced override, LSP violation

// Composition — behaviors combine freely
class Duck {
  constructor(flyBehavior, swimBehavior, quackBehavior) { ... }
}
```

## Separation of Concerns

**Definition**: Distinct responsibilities (e.g. business logic, data access, presentation, cross-cutting
concerns like logging/auth) should live in distinct, independently-reasoned-about units.

**Symptom of violation**: A single function mixes input validation, business rule evaluation, database
calls, and response formatting — testing the business rule requires standing up (or mocking) the whole
stack.

**Fix**: Layer by concern (e.g. handler → service → repository) or, for cross-cutting concerns, extract
to middleware/decorators/aspects rather than repeating the concern inline in every business method.

**Relationship to SRP**: Separation of Concerns is SRP applied at the architectural-layer level rather
than the single-class level — same underlying idea, larger unit of analysis.

## Applying These Heuristics Together

These are heuristics, not laws — they exist in tension (DRY vs. KISS, YAGNI vs. OCP) by design. When two
heuristics point in different directions on a real piece of code, name the tension explicitly and pick
based on which failure mode is more expensive *for this specific system*, not by mechanically applying
whichever heuristic comes to mind first.
