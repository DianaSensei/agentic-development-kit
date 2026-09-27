---
type: regex
# The description promises ROUND_HALF_EVEN; the diff truncates with math.floor.
pattern: '(floor|truncat)[\s\S]{0,600}(half[ _-]?even|banker)|(half[ _-]?even|banker)[\s\S]{0,600}(floor|truncat)'
flags: i
---
