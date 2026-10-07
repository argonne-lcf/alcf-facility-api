# Facility API Prototype - VM Setup

Instructions and notes on how to setup a VM to serve the ALCF Facility API with Nginx.

## VM environment

Make sure the VM has access to the latest packages
```bash
sudo apt update && sudo apt upgrade -y
```

Install `rotatelogs` (part of `apache2-utils`):
```bash
sudo apt install apache2-utils
```

Add packages
```bash
sudo apt install make
```

## Firewall

Make sure the Uncomplicated Firewall (UFW) is disabled and reset to its original setting:
```bash
sudo ufw disable
sudo ufw reset
```

Deny all incoming connections except ssh, and allow all outgoing connections:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
```

Allow incoming HTTPS connections:
```bash
sudo ufw allow 443
```

Enable the firewall and check its status:
```bash
sudo ufw enable
sudo ufw status verbose numbered
```

Make sure you see `22/tcp ALLOW IN Anywhere` before logging out of the VM, otherwise you will not be able to ssh back in.

## Nginx

If not already installed, install Nginx:
```bash
sudo apt install nginx -y
```

Check status to make sure it's running
```bash
sudo systemctl status nginx
```

## API user account

Create a new Unix user (`apiuser`) with a home directory to allow others to operate and maintain the API service (**DO NOT create users with UID and GUI above 1000**):

```bash
sudo useradd -K UID_MIN=800 -K UID_MAX=850 -K GID_MIN=800 -K GID_MAX=850 -m apiuser
```

Look at the UID, GID, and home directory of the `apiuser` account:
```bash
cat /etc/passwd | grep "apiuser"
```

## Create postgres database

Install postgres:
```bash
sudo apt update
sudo apt install -y postgresql postgresql-client
psql --version
```

Postgres runs as a systemctl service. Check its status:
```bash
sudo systemctl status postgresql
```

Start a Postgres shell as the admin user, and create `apiuser` user for the database (the user needs to be the same as the Unix user you created in the previous section). **Do not** use `@ : / ? # [ ] % < > !` characters for the password, it will cause issue when parsing the password from the database URL.
```bash
sudo -u postgres psql # Or with local Mac: psql postgres
CREATE USER apiuser WITH PASSWORD 'your-password-here';
```

Create database:
```bash
CREATE DATABASE facilityapi_db OWNER apiuser;
```

Grant all privilages:
```bash
GRANT ALL PRIVILEGES ON DATABASE facilityapi_db TO apiuser;
```

Quit postgres shell:
```bash
\q
```

Sudo into the `apiuser` and and test that you can connect to database:
```bash
sudo -u apiuser /bin/bash
psql -U apiuser -d facilityapi_db
\q
```

The URL of the database will be:
```bash
# Without password
DATABASE_URL=postgresql+asyncpg://apiuser@localhost/facilityapi_db

# With password (needed for VM deployment)
DATABASE_URL=postgresql+asyncpg://apiuser:your_password@localhost:5432/facilityapi_db
```

Check if you have your tables created:
```bash
psql -U apiuser -d facilityapi_db -c "\dt"
```

Check how many entries you have for status tables:
```bash
psql -U apiuser -d facilityapi_db -c "SELECT 'facility' as table_name, COUNT(*) as row_count FROM facility UNION ALL SELECT 'location', COUNT(*) FROM location UNION ALL SELECT 'site', COUNT(*) FROM site UNION ALL SELECT 'resource', COUNT(*) FROM resource UNION ALL SELECT 'incident', COUNT(*) FROM incident UNION ALL SELECT 'event', COUNT(*) FROM event;"
```

Check status of resources according to the database:
```bash
psql -U apiuser -d facilityapi_db -c "SELECT id, name, type, current_status FROM resource;"
```

Check how many entries you have for task and user:
```bash
psql -U apiuser -d facilityapi_db -c "SELECT 'user' as table_name, COUNT(*) as row_count FROM \"user\" UNION ALL SELECT 'task', COUNT(*) FROM task;"
```

Check basic details on each user:
```bash
psql -U apiuser -d facilityapi_db -c "SELECT username, idp_name, auth_service FROM \"user\";"
```

**DANGER ZONE** Clear all data from all table:
```bash
# DANGER ZONE
psql -U apiuser -d facilityapi_db -c "
TRUNCATE TABLE event, incident, resource, site, location, facility CASCADE;
"
# DANGER ZONE
```

**DANGER ZONE** Clear event and incident tables only:
```bash
# DANGER ZONE
psql -U apiuser -d facilityapi_db -c "
TRUNCATE TABLE event, incident CASCADE;
"
# DANGER ZONE
```

Check access logs:
```bash
psql -U apiuser -d facilityapi_db -c "SELECT id, user_id, created_at, api_route FROM accesslog;"
```

Check compute logs:
```bash
psql -U apiuser -d facilityapi_db -c "SELECT id, access_log_id, alcf_username FROM computelog;"
```

Check task logs:
```bash
psql -U apiuser -d facilityapi_db -c "SELECT id, globus_endpoint_id, globus_function_id FROM task;"
```

### Migrate database if fields are changed

Example with task, which changed `command` to `task_command`. Check current columns:
```bash
psql -U apiuser -d facilityapi_db -c "\d task"
```

Apply the migration:
```bash
psql -U apiuser -d facilityapi_db -c "ALTER TABLE task RENAME COLUMN command TO task_command;"
```

Add endpoint and function id to Task
```bash
psql -U apiuser -d facilityapi_db -c "ALTER TABLE task ADD COLUMN globus_endpoint_id TEXT;"
psql -U apiuser -d facilityapi_db -c "ALTER TABLE task ADD COLUMN globus_function_id TEXT;"
```

Add `type_urn` in resources:
```bash
psql -U apiuser -d facilityapi_db -c "ALTER TABLE resource ADD COLUMN type_urn TEXT;"
```

## Redis cache

Install redis
```bash
sudo apt update
sudo apt install -y redis-server
```

Enable Redis as a systemctl service
```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
systemctl status redis-server
```

Check connectivity
```bash
redis-cli ping
```

## FastAPI application

Sudo into the `apiuser` account and go to its home directory:
```bash
sudo -u apiuser /bin/bash
cd ~
```

Create directory for the gunicorn logs:
```bash
mkdir /var/log/alcf-facility-api/v1
mkdir /var/log/alcf-facility-api/v2
```

Install `uv`:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# You may need to exit the shell and come back to see the uv package
```

Prepare folders:
```bash
mkdir /home/apiuser/v1
mkdir /home/apiuser/v2
```

Clone the alcf-facility-api code, and follow the instructions in the previous README file to install the application:
```bash
# v1
cd /home/apiuser/v1
git clone https://github.com/argonne-lcf/alcf-facility-api
cd alcf-facility-api
git checkout -b alcf-v1 --track origin/alcf-v1

# v2
cd /home/apiuser/v2
git clone https://github.com/argonne-lcf/alcf-facility-api
cd alcf-facility-api
git checkout -b alcf-v2 --track origin/alcf-v2
```

Installation instructions can be found in the main README file of this Git repository. Make sure you install miniconda in the home directory of the `apiuser`.

## Gunicorn service

As a privileged user (not `apiuser`), add the Gunicorn service file to the `systemd/system/` folder, and give the ownership to `apiuser`:
```bash
sudo cp /home/apiuser/v2/alcf-facility-api/alcf/vm_setup/gunicorn.service /etc/systemd/system/gunicorn.service
sudo chown apiuser:apiuser /etc/systemd/system/gunicorn.service

sudo cp /home/apiuser/v2/alcf-facility-api/alcf/vm_setup/gunicorn-v2.service /etc/systemd/system/gunicorn-v2.service
sudo chown apiuser:apiuser /etc/systemd/system/gunicorn-v2.service
```

Enable the service with `systemctl`:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl enable gunicorn-v2
```

Start, stop, and restart Gunicorn with:
```bash
sudo systemctl start gunicorn
sudo systemctl status gunicorn
sudo systemctl stop gunicorn
sudo systemctl restart gunicorn

sudo systemctl start gunicorn-v2
sudo systemctl status gunicorn-v2
sudo systemctl stop gunicorn-v2
sudo systemctl restart gunicorn-v2
```

Follow the gunicorn logs with:
```bash
sudo tail -f -n 1000 /var/logs/alcf-facility-api/logs/fastapi.access.log
sudo tail -f -n 1000 /var/logs/alcf-facility-api/logs/fastapi.error.log
```

```bash
# v1
tail -f -n 1000 /var/log/alcf-facility-api/v1/log.out
tail -f -n 1000 /var/log/alcf-facility-api/v1/log.err 

# v2
tail -f -n 1000 /var/log/alcf-facility-api/v2/log.out
tail -f -n 1000 /var/log/alcf-facility-api/v2/log.err 
```

Stdout activity logs can be monitored with filters using `jq`:

```bash
# Filter logs by API component
tail -f -n 1000 /var/log/alcf-facility-api/v2/log.out | jq 'select (.stream=="compute")'

# Filter logs by API component and only show a subset of fields
tail -f -n 1000 /var/log/alcf-facility-api/v2/log.out | jq 'select (.stream=="compute") | {api_function, status_code, alcf_username}'

# Regular monitoring
tail -f -n 1000 /var/log/alcf-facility-api/v2/log.out | jq {'stream,api_function,status_code,user_name,error'}

# See error logs
tail -f -n 1000 /var/logs/alcf-facility-api/err.out
```

## Nginx web server

As a privileged user (not `apiuser`), make a copy of the original nginx config file:
```bash
sudo cp /etc/nginx/sites-enabled/default /etc/nginx/default_original_backup
```

Overwrite the Nginx configuration file:
```bash
sudo cp /home/apiuser/v2/alcf-facility-api/alcf/vm_setup/default /etc/nginx/sites-enabled/default
```

This assumes you already have a self-signed SSL certificate defined in the `/etc/nginx/snippets/snakeoil.conf` file:
```bash
ssl_certificate /etc/ssl/certs/ssl-cert-snakeoil.pem;
ssl_certificate_key /etc/ssl/private/ssl-cert-snakeoil.key;
```

**Do not** use self-signed SSL certificates in production.

Restart Nginx to load the new configuration file:
```bash
sudo systemctl restart nginx
```
