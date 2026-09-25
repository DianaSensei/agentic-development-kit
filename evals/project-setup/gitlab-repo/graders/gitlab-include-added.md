---
type: regex
target: { source: file, path: .gitlab-ci.yml }
pattern: 'remote:\s*["'']?https://raw\.githubusercontent\.com/DianaSensei/agentic-development-kit/[^/\s]+/ci/gitlab/independent-review\.yml'
---
