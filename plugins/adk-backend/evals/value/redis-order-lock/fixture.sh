#!/usr/bin/env bash
# A distributed lock for order processing. Measures what redis-skill adds: a TTL on the lock and release only by its owner.
set -euo pipefail
cat > pom.xml <<XML
<project><parent><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-parent</artifactId><version>3.3.2</version></parent>
<dependencies><dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-data-redis</artifactId></dependency></dependencies></project>
XML
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm init
