#!/bin/bash

read -sp "username: " username
echo
read -sp "cryptoauth: " passvar
echo

response=$(curl -s -k -X POST "https://keycloak.alcf.anl.gov/realms/ALCF-PBS/protocol/openid-connect/token" \
 -H 'Content-Type: application/x-www-form-urlencoded' \
 -d 'grant_type=password' \
 -d 'client_id=ALCF-PBS-PUBLIC' \
 -d "username=${username}" \
 -d "password=${passvar}")

echo "$response" | jq