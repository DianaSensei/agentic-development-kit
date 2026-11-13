#!/usr/bin/env bash
# A live index whose mapping must change. Measures what elasticsearch-skill adds over a bare model: reindex behind an alias, never an in-place edit.
set -euo pipefail
cat > pom.xml <<XML
<project><parent><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-parent</artifactId><version>3.3.2</version></parent>
<dependencies><dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-data-elasticsearch</artifactId></dependency></dependencies></project>
XML
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm init
