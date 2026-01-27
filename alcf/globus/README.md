# Globus Configuration

## Create Facility API Filesystem Scope

Export your Service API Globus client credentials:
```bash
CLIENT_ID="<Your-Service-API-Client-UUID>"
CLIENT_SECRET="<Your-Service-API-Client-Secret>"
```

Edit the `filesystem_scope.json` details if needed. It should include the following 2 scopes:
- Globus Compute: `58ce1893-b1fe-4753-a697-7138ceb95adb` 
- Globus Groups: `73320ffe-4cb4-4b25-a0a3-83d53d59ce4f`

Add the scope to your client:
```bash
curl -X POST -s --user "$CLIENT_ID:$CLIENT_SECRET" \
  https://auth.globus.org/v2/api/clients/$CLIENT_ID/scopes \
  -H "Content-Type: application/json" \
  -d @filesystem_scope.json
```

Look at your API client details:
```bash
curl -s --user $CLIENT_ID:$CLIENT_SECRET https://auth.globus.org/v2/api/clients/$CLIENT_ID | jq
```

Create variable for your API client's scope
```bash
SCOPE_ID=<Your-Scope-UUID>
```

Check details of your API scope
```bash
curl -s --user $CLIENT_ID:$CLIENT_SECRET \
    https://auth.globus.org/v2/api/clients/$CLIENT_ID/scopes/$SCOPE_ID | jq
```
