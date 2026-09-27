---
type: regex
# A proposed profile line: raise a domain error rather than return None on failure.
pattern: '(rais\w*|exception|error)[^\n]{0,160}(None|swallow)|(None|swallow)[^\n]{0,160}(rais\w*|exception|error)'
flags: i
---
