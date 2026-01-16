# Facility API Prototype - VM Setup

Instructions and notes on how to setup a VM to serve the ALCF Facility API with Nginx.

## VM environment

Make sure the VM has access to the latest packages
```bash
sudo apt update && sudo apt upgrade -y
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

## Create postgres database

Create username and password for the database
```bash
psql
CREATE USER facilityapi_user WITH PASSWORD 'your-password-here';
```

Create database
```bash
CREATE DATABASE facilityapi_db
    OWNER facilityapi_user
    ENCODING 'UTF8'
    TEMPLATE template0;
```

Quit postgres shell
```bash
\q
```

Connect to database
```bash
psql -U facilityapi_user -d facilityapi_db
```

The URL of the database will be:
```bash
# Without password
DATABASE_URL=postgresql+asyncpg://facilityapi_user@localhost/facilityapi_db

# With password
DATABASE_URL=postgresql+asyncpg://facilityapi_user:your_password@localhost:5432/facilityapi_db
```

Check if you have your tables created:
```bash
psql -U facilityapi_user -d facilityapi_db -c "\dt"
```

Check how many entries you have for each table:
```bash
psql -U facilityapi_user -d facilityapi_db -c "SELECT 'facility' as table_name, COUNT(*) as row_count FROM facility UNION ALL SELECT 'location', COUNT(*) FROM location UNION ALL SELECT 'site', COUNT(*) FROM site UNION ALL SELECT 'resource', COUNT(*) FROM resource UNION ALL SELECT 'incident', COUNT(*) FROM incident UNION ALL SELECT 'event', COUNT(*) FROM event;"
```

Check status of resources according to the database:
```bash
psql -U facilityapi_user -d facilityapi_db -c "SELECT id, name, type, current_status FROM resource;"
```

**DANGER ZONE** Clear all data from all table:
```bash
# DANGER ZONE
psql -U facilityapi_user -d facilityapi_db -c "
TRUNCATE TABLE event, incident, resource, site, location, facility CASCADE;
"
# DANGER ZONE
```

**DANGER ZONE** Clear event and incident tables only:
```bash
# DANGER ZONE
psql -U facilityapi_user -d facilityapi_db -c "
TRUNCATE TABLE event, incident CASCADE;
"
# DANGER ZONE
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

## FastAPI application

Sudo into the `apiuser` account and go to its home directory:
```bash
sudo -u apiuser /bin/bash
cd ~
```

Clone the alcf-facility-api code, and follow the instructions in the previous README file to install the application:
```bash
git clone https://github.com/argonne-lcf/alcf-facility-api
git checkout -b alcf-deployment --track origin/alcf-deployment
```

Installation instructions can be found in the main README file of this Git repository. Make sure you install miniconda in the home directory of the `apiuser`.

## Gunicorn service

As a privileged user (not `apiuser`), add the Gunicorn service file to the `systemd/system/` folder, and give the ownership to `apiuser`:
```bash
sudo cp /home/apiuser/alcf-facility-api/alcf/vm_setup/gunicorn.service /etc/systemd/system/gunicorn.service
sudo chown apiuser:apiuser /etc/systemd/system/gunicorn.service
```

Enable the service with `systemctl`:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
```

Start, stop, and restart Gunicorn with:
```bash
sudo systemctl start gunicorn
sudo systemctl stop gunicorn
sudo systemctl restart gunicorn
```

Check the current status of Gunicorn:
```bash
sudo systemctl status gunicorn
```

Follow the service logs with:
```bash
sudo tail -f -n 1000 /home/apiuser/alcf-facility-api/logs/fastapi.access.log
sudo tail -f -n 1000 /home/apiuser/alcf-facility-api/logs/fastapi.error.log
```

## Nginx web server

As a privileged user (not `apiuser`), make a copy of the original nginx config file:
```bash
sudo cp /etc/nginx/sites-enabled/default /etc/nginx/default_original_backup
```

Overwrite the Nginx configuration file:
```bash
sudo cp /home/apiuser/alcf-facility-api/vm_setup/default /etc/nginx/sites-enabled/default
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
