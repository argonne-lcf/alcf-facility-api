#!/bin/bash

read -sp "username: " username
echo
read -sp "cryptoauth: " passvar
echo

# EDTB
response=$(curl -s -k -X POST "https://keycloak.alcf.anl.gov/realms/PBS-EDTB/protocol/openid-connect/token" \
 -H 'Content-Type: application/x-www-form-urlencoded' \
 -d 'grant_type=password' \
 -d 'client_id=PBS-EDTB-PUBLIC' \
 -d "username=${username}" \
 -d "password=${passvar}")

# SIRIUS
#response=$(curl -s -k -X POST "https://keycloak.alcf.anl.gov/realms/PBS-SIRIUS/protocol/openid-connect/token" \
# -H 'Content-Type: application/x-www-form-urlencoded' \
# -d 'grant_type=password' \
# -d 'client_id=PBS-SIRIUS-PUBLIC' \
# -d "username=${username}" \
# -d "password=${passvar}")

echo "$response" | jq