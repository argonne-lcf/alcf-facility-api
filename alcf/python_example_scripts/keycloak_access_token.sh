#!/bin/bash

read -sp "username: " username
echo
read -sp "cryptoauth: " passvar
echo

response=$(curl -s -k -X POST "https://keycloak.alcf.anl.gov/realms/PBS-EDTB/protocol/openid-connect/token" \
 -H 'Content-Type: application/x-www-form-urlencoded' \
 -d 'grant_type=password' \
 -d 'client_id=PBS-EDTB-PUBLIC' \
 -d "username=${username}" \
 -d "password=${passvar}")

echo "$response" | jq