# SOLID Principles

Five class/module-level design principles. They exist to keep a codebase *changeable* - cheap to extend,
safe to modify, easy to test in isolation. Judge every violation by what change becomes expensive or
risky, not by the label alone.

## S - Single Responsibility Principle (SRP)

**Definition**: A class/module should have exactly one reason to change.

**Symptom of violation**: The class's methods cluster into groups that touch unrelated stakeholders or
unrelated data. A change requested by "the billing team" and a change requested by "the notification
team" both require editing the same file.

```
// Violates SRP - one reason to change becomes three
class OrderService {
  process(order)         // business logic
  chargeCard(order)       // payment concern
  sendConfirmationEmail(order) // notification concern
  writeAuditLog(order)    // compliance concern
}
```

**Fix**: Extract each concern into its own collaborator; `OrderService` orchestrates.

**When NOT to over-apply**: A 20-line class with two small, always-co-changing methods does not need to
be split "for SRP." SRP is about reasons to change driven by different stakeholders/axes of change, not
about method count. Splitting code that always changes together adds indirection without adding
flexibility.

## O - Open/Closed Principle (OCP)

**Definition**: A module should be open for extension, closed for modification - add new behavior
without editing existing, tested code.

**Symptom of violation**: A recurring `if/else` or `switch` on a type code that grows every time a new
case is added, scattered across multiple files.

```
// Violates OCP - every new payment type edits this function
function calculateFee(type) {
  if (type === "credit") return amount * 0.03;
  if (type === "debit")  return amount * 0.01;
  if (type === "crypto") return amount * 0.05; // added later, risks regressing the others
}
```

**Fix**: Polymorphism or a strategy/registry pattern - new payment types register a new implementation
without touching existing ones.

**When NOT to over-apply**: Don't build a plugin/strategy abstraction for a `switch` with 2 stable cases
that changes once a year. OCP pays off when new cases are added *frequently* and independently; applied
prematurely it's speculative generality (YAGNI violation).

## L - Liskov Substitution Principle (LSP)

**Definition**: A subtype must be substitutable for its base type without altering the correctness of
the program - callers relying on the base type's contract must not break when handed a subtype.

**Symptom of violation**: A subclass overrides a method to throw, no-op, or narrow the accepted input
range in a way the base type's callers don't expect.

```
// Violates LSP - callers of Bird.fly() break on Penguin
class Bird { fly() { ... } }
class Penguin extends Bird { fly() { throw new Error("can't fly"); } }
```

**Fix**: Model the capability, not the taxonomy - `FlyingBird` vs. `FlightlessBird`, or a `canFly()`
capability check, instead of forcing every bird through one interface.

**Concrete failure mode this prevents**: Runtime type-checking (`if (obj instanceof Penguin) skip()`)
scattered through calling code - the clearest sign LSP has already been violated upstream.

## I - Interface Segregation Principle (ISP)

**Definition**: Clients should not be forced to depend on methods they don't use - prefer several small,
focused interfaces over one large one.

**Symptom of violation**: A class implements an interface with 10 methods but provides real
implementations for 2 and stubs/`NotImplementedError` for the rest.

```
// Violates ISP
interface Worker { work(); eat(); sleep(); }
class RobotWorker implements Worker {
  work() { ... }
  eat()  { throw new Error("robots don't eat"); }  // forced, meaningless
  sleep(){ throw new Error("robots don't sleep"); }
}
```

**Fix**: Split into `Workable`, `Eatable`, `Sleepable`; `RobotWorker` implements only `Workable`.

**When NOT to over-apply**: Splitting a 3-method interface used identically by every implementer into
three 1-method interfaces adds ceremony with no real client ever needing a subset.

## D - Dependency Inversion Principle (DIP)

**Definition**: High-level modules should not depend on low-level modules; both should depend on
abstractions. Abstractions should not depend on details; details depend on abstractions.

**Symptom of violation**: Business logic directly instantiates and calls a concrete infrastructure class
(a specific DB driver, HTTP client, filesystem call), making the business logic untestable without that
infrastructure being live.

```
// Violates DIP - OrderService is welded to PostgresOrderRepo
class OrderService {
  constructor() { this.repo = new PostgresOrderRepo(); }
}

// Follows DIP - depends on an abstraction, injected
class OrderService {
  constructor(repo: OrderRepository) { this.repo = repo; }
}
```

**Fix**: Depend on an interface/port; inject the concrete implementation (constructor injection, a DI
container, or manual wiring at the composition root).

**Concrete failure mode this prevents**: Unit tests for business logic that require a real database,
network, or filesystem - the clearest sign DIP is missing.

## Applying SOLID as a Set

The five principles reinforce each other: DIP is often *how* you satisfy OCP (extend via new
implementations of an abstraction); ISP is what keeps the abstractions DIP introduces from becoming
another SRP violation. Don't evaluate them in isolation on a real review - a DIP violation and an OCP
violation are frequently the same root cause seen from two angles.

**The overriding rule**: SOLID exists to make future change cheap. If a "fix" makes the code harder to
read today for a change that is unlikely to ever happen, it has failed the principle's actual purpose
even while satisfying its letter.
