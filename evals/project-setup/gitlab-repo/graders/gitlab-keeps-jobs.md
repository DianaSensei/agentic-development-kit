---
type: regex
target: { source: file, path: .gitlab-ci.yml }
pattern: 'unit-tests:\s*\n\s+stage:\s*verify[\s\S]*npm test'
---
