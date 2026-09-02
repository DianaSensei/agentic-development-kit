# Refactoring Patterns

## Method

Six named patterns for restructuring legacy code without changing its observable behavior. Each
follows the same underlying shape: introduce a seam (an interface/abstraction boundary) around the
thing being changed, so the change can happen behind that seam without touching every call site.

**Branch by Abstraction** - the general-purpose version of the seam idea, useful whenever a large
piece of behavior needs to be replaced incrementally without a big-bang cutover:
1. Define an abstraction (interface) for the behavior being replaced.
2. Implement that abstraction by wrapping the existing legacy behavior, unchanged.
3. Implement a second, new version of the abstraction.
4. Migrate every call site to depend on the abstraction only - never on either concrete
   implementation directly.
5. Once all call sites depend on the abstraction, switch which implementation is active via
   configuration/dependency injection - no further call-site changes are needed to flip back and
   forth, which is what makes the cutover reversible.

**Extract Service** - applied when one class or function has accumulated too many responsibilities
(e.g. validation, pricing, payment, notification, and inventory all inside one "create order" method).
Split each responsibility into its own single-purpose collaborator, then have a thinner coordinator
call each collaborator in sequence - and push genuinely non-critical steps (notifications, non-blocking
side effects) to run in the background rather than in the critical path.

**Adapter** - applied when a legacy interface doesn't match the shape modern code expects (different
naming conventions, synchronous where new code expects asynchronous, etc.). Define the interface new
code should depend on, then write an adapter that translates calls between the legacy shape and the
modern shape. New code depends only on the modern interface and never touches the legacy shape
directly - the adapter is the only thing that knows both shapes exist.

**Facade** - applied when several legacy subsystems must be coordinated together (e.g. an auth system,
a session manager, and an audit logger that must all be called in the right order for a "login" to
happen correctly). Wrap the coordination logic behind one simplified interface; callers call one
method instead of re-implementing the coordination themselves at every call site.

**Replace Algorithm** - applied when an existing algorithm has a correctness or performance problem
but its callers must not be disrupted while it's replaced. Extract the algorithm behind a
strategy-style interface, implement the improved algorithm behind the same interface, then select
which strategy is active via the same kind of flag/config used in Branch by Abstraction - so the
algorithm swap is independently revertable from anything else in the codebase.

**Introduce Repository** - applied when data-access logic (raw queries) is scattered directly inside
business logic or controllers instead of being centralized. Define a repository interface for the
specific data operations actually needed, implement it first against the existing/legacy access
pattern (so nothing breaks), then implement a modern version once ready. Callers depend on the
repository interface and never issue raw queries themselves again.

## Boundary

- Every one of these patterns is about restructuring code *without changing observable behavior* -
  that's the entire point of doing it this way instead of rewriting. If a change is expected to alter
  behavior, that's not a refactor; write characterization tests first (see the testing reference) so
  any unintended behavior change is caught, and treat intentional behavior changes as a separate,
  explicitly-labeled step from the structural refactor.
- These patterns provide the *seam* to swap an implementation through safely - they do not make the
  decision of which concrete new technology, library, or algorithm to swap in. That's a separate
  design decision that happens before or alongside applying the pattern, not something the pattern
  itself resolves.
- Introducing an abstraction has a cost (an extra layer of indirection) - apply these patterns where
  the incremental-migration benefit justifies that cost, not as a default way to write new code that
  isn't being migrated from anything.
