# RPC (gRPC/Protobuf)

## When to use
- INTERNAL service-to-service communication that needs high performance, or needs
  streaming (server-side, client-side, or bidirectional streaming).
- NOT suitable for a public API facing the browser directly - browsers cannot call
  plain gRPC, a proxy such as `grpc-web` is needed if it must be exposed to the browser.

## Designing the `.proto`
- **Field numbers must NEVER be changed/reused after being published** - this is the
  most serious breaking change in Protobuf, since the wire format relies on field
  numbers, not names. Only add new fields with new field numbers; mark deleted field
  numbers as `reserved N;` to prevent anyone from accidentally reusing that number
  later.
- New fields MUST be optional (or have a sensible default value) so as not to break
  older clients that haven't updated - the same backward-compatibility principle as
  REST/GraphQL.
- Name messages/fields following convention: `snake_case` for fields (Protobuf
  standard), `PascalCase` for message names.

## Service Definition
```protobuf
service OrderService {
  rpc GetOrder(GetOrderRequest) returns (Order);
  rpc StreamOrderUpdates(StreamRequest) returns (stream OrderUpdate); // server streaming
}
```
- Method names are clear verbs (`GetOrder`, `CreateOrder`) - unlike REST, having a verb
  in the RPC method name is normal since this isn't resource-oriented.

## Versioning
- Encode the version into the package name (`package com.example.order.v1;`) when a
  breaking change is needed - create a new `v2` package instead of trying to cram
  backward compatibility into the same message when the change is too large, to
  preserve the meaning of "1 version = 1 fixed contract".

## Deadline & Timeout
- Always set a client-side deadline for every RPC call - to avoid waiting indefinitely
  when a downstream service is slow/hung. Don't rely on the library's default timeout
  (usually too long or nonexistent).
- Deadlines should propagate through the whole call chain (deadline propagation) if A
  calls B calls C - C should not have a deadline longer than the remaining time of the
  original deadline from A.

## Error Handling
- Use gRPC's standard status codes (`INVALID_ARGUMENT`, `NOT_FOUND`,
  `PERMISSION_DENIED`, `DEADLINE_EXCEEDED`...) instead of defining custom error codes -
  gRPC clients/tooling already understand these statuses.
- Use `google.rpc.ErrorDetails` (or an equivalent) to carry structured error information
  when more detail than a plain status code is needed.
