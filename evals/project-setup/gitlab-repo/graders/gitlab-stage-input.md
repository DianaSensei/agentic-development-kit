---
type: regex
target: { source: file, path: .gitlab-ci.yml }
pattern: '\n([ \t]*)inputs:[ \t]*\n(?:\1[ \t]+\S[^\n]*\n)*?\1[ \t]+stage:[ \t]*["'']?(?:build|verify)\b'
---
