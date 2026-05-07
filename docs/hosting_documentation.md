# Hosting Documentation

`python-cluedo` and its frontend are self-hosted on a Raspberry Pi Zero W and available at [cluedosolver.com](https://cluedosolver.com/).

- Reserved local IP address: `<local-ip>`
- OS version: Raspbian GNU/Linux 12 (bookworm) (via `cat /etc/*release`)

SSH into the Raspberry Pi from the local network:

```
ssh pi@<local-ip>
```

## Configure the Raspberry Pi

- Enable public key authentication using `ssh-copy-id pi@<local-ip>`.
- Disable password login by setting `PasswordAuthentication no` in `/etc/ssh/sshd_config`.

## Configure the `cluedo-web-solver` backend service

Entrypoint: `web_solver_server.py`

Clone the `python-cluedo` repo:

```
git clone https://github.com/keeganmjgreen/python-cluedo.git
```

Install `python3-dev` to fix `error: Python.h: No such file or directory` when compiling `pypblib`:

```
sudo apt update
sudo apt install python3-dev
```

Create the Python virtual environment:

```
cd ~/python-cluedo/
uv sync --no-dev
```

The first `uv sync` will compile Pydantic, `python-sat`, etc. and thus take some time on the slow hardware.

Create, enable, and start the `cluedo-web-solver` service:

```
sudo cat <<EOF > /etc/systemd/system/cluedo-web-solver.service
[Unit]
Description=Cluedo Web Solver
After=network.target

[Service]
WorkingDirectory=/home/pi/python-cluedo/
ExecStart=/home/pi/python-cluedo/.venv/bin/uvicorn web_solver_server:app --host 0.0.0.0 --port 5005
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reexec
sudo systemctl enable cluedo-web-solver
sudo systemctl start cluedo-web-solver
```

This ensures that the backend starts automatically when the Raspberry Pi boots.

## Build and deploy the frontend

Run the "Build and Deploy" VS Code task (from `tasks.json`) to build the React app to `cluedo-web-solver/dist/` and `rsync` it to the Raspberry Pi:

```
/srv/cluedo-web-solver/dist/
├── index.html
└── assets/
    ├── index-XYZ.css
    └── index-XYZ.js
```

This requires giving `rsync` access to `srv/cluedo-web-solver/`; do one of the following:

- `sudo visudo` and append `pi ALL=(ALL) NOPASSWD: /usr/bin/rsync`
- `sudo chown -R pi:pi /srv/cluedo-web-solver`

## Configure the nginx server

Install nginx:

```
sudo apt update
sudo apt install nginx
```

Global nginx configuration:

```
sudo cat <<EOF > /etc/nginx/nginx.conf
user www-data;
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    include mime.types;
    default_type application/octet-stream;

    sendfile on;

    include /etc/nginx/sites-enabled/*;

    limit_req_zone \$binary_remote_addr zone=cluedo-web-solver:10m rate=5r/s;
}
EOF
```

Configure `cluedo-web-solver` as an available site:

```
sudo cat <<EOF > /etc/nginx/sites-available/cluedo-web-solver
server {
    listen 80;

    root /srv/cluedo-web-solver/dist/;
    index index.html;

    location / {
        try_files \$uri /index.html;
    }
    location /socket.io/ {
        limit_req zone=cluedo-web-solver burst=20 nodelay;

        proxy_pass http://localhost:5005;
        proxy_http_version 1.1;

        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
    }
}
EOF
```

Create a symbolic link to `sites-enabled/` to enable the `cluedo-web-solver` site:

```
sudo ln -s /etc/nginx/sites-available/cluedo-web-solver /etc/nginx/sites-enabled/
```

Remove the `default` site (nginx welcome page):

```
sudo rm /etc/nginx/sites-enabled/default
```

Check the configuration and start or reload nginx from it:

```
sudo nginx -t
sudo systemctl start nginx
sudo systemctl reload nginx
```

## Expose to the internet

Install the Cloudflare daemon ([reference](https://stackoverflow.com/questions/64299127/getting-illegal-instruction-error-when-trying-to-install-cloudflared-on-a-fres/78975712#78975712)):

```
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm.deb
sudo dpkg -i --force-architecture cloudflared-linux-arm.deb
```

Log into Cloudflare:

```
cloudflared tunnel login
```

List available Cloudflare tunnels:

```
cloudflared tunnel list
```

Install (and start) the tunnel service:

```
sudo cloudflared service install $(cloudflared tunnel token cluedosolver-tunnel)
```

## Other helpful references

- https://websocket.org/guides/reconnection/
- https://developers.cloudflare.com/tunnel/setup/
