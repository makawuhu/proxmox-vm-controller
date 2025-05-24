#!/bin/bash

# Create systemd service file
cat > /etc/systemd/system/vm-controller.service << 'EOF'
[Unit]
Description=VM Controller API
After=network.target
Wants=network.target

[Service]
Type=simple
User=vmcontroller
Group=vmcontroller
WorkingDirectory=/opt/vm-controller
Environment=PATH=/opt/vm-controller/venv/bin
Environment=FLASK_ENV=production
ExecStart=/opt/vm-controller/venv/bin/python app.py
Restart=always
RestartSec=5

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/vm-controller

[Install]
WantedBy=multi-user.target
EOF

# Create startup script for easier management
cat > /opt/vm-controller/start.sh << 'EOF'
#!/bin/bash
cd /opt/vm-controller
source venv/bin/activate
python app.py
EOF

chmod +x /opt/vm-controller/start.sh

# Create environment setup script
cat > /opt/vm-controller/setup-env.sh << 'EOF'
#!/bin/bash

# Configuration script for VM Controller
echo "=== VM Controller Environment Setup ==="

# Update configuration
read -p "Proxmox host IP [192.168.1.100]: " PROXMOX_IP
PROXMOX_IP=${PROXMOX_IP:-192.168.1.100}

read -p "Proxmox SSH user [root]: " PROXMOX_USER
PROXMOX_USER=${PROXMOX_USER:-root}

read -p "Gaming VM ID [100]: " GAMING_VM_ID
GAMING_VM_ID=${GAMING_VM_ID:-100}

read -p "AI/Creative VM ID [101]: " AI_VM_ID
AI_VM_ID=${AI_VM_ID:-101}

read -s -p "API Key for web interface: " API_KEY
echo

# Update app.py with new configuration
sed -i "s/PROXMOX_HOST = .*/PROXMOX_HOST = \"$PROXMOX_IP\"/" app.py
sed -i "s/PROXMOX_USER = .*/PROXMOX_USER = \"$PROXMOX_USER\"/" app.py
sed -i "s/API_KEY = .*/API_KEY = \"$API_KEY\"/" app.py
sed -i "s/\"id\": 100/\"id\": $GAMING_VM_ID/" app.py
sed -i "s/\"id\": 101/\"id\": $AI_VM_ID/" app.py

echo "✅ Configuration updated!"
echo "🔐 Remember to configure SSH key access to Proxmox host"
echo "🚀 Start the service with: sudo systemctl start vm-controller"
EOF

chmod +x /opt/vm-controller/setup-env.sh

# Create installation script for easy deployment
cat > /opt/vm-controller/install.sh << 'EOF'
#!/bin/bash

echo "=== Installing VM Controller ==="

# Install dependencies
apt update
apt install -y python3 python3-pip python3-venv openssh-client

# Create app user if doesn't exist
if ! id "vmcontroller" &>/dev/null; then
    useradd -m -s /bin/bash vmcontroller
    echo "✅ Created vmcontroller user"
fi

# Set up Python environment
python3 -m venv /opt/vm-controller/venv
source /opt/vm-controller/venv/bin/activate
pip install flask

# Set permissions
chown -R vmcontroller:vmcontroller /opt/vm-controller
chmod +x /opt/vm-controller/*.sh

# Install systemd service
systemctl daemon-reload
systemctl enable vm-controller

echo "✅ Installation complete!"
echo "📝 Run ./setup-env.sh to configure"
echo "🔑 Set up SSH keys between container and Proxmox host"
echo "🚀 Start with: sudo systemctl start vm-controller"
EOF

chmod +x /opt/vm-controller/install.sh

# Create SSH key setup helper
cat > /opt/vm-controller/setup-ssh.sh << 'EOF'
#!/bin/bash

echo "=== SSH Key Setup Helper ==="

USER_HOME="/home/vmcontroller"
SSH_DIR="$USER_HOME/.ssh"

# Ensure SSH directory exists
mkdir -p $SSH_DIR
chown vmcontroller:vmcontroller $SSH_DIR
chmod 700 $SSH_DIR

# Generate SSH key if it doesn't exist
if [ ! -f "$SSH_DIR/id_rsa" ]; then
    sudo -u vmcontroller ssh-keygen -t rsa -b 4096 -f "$SSH_DIR/id_rsa" -N ""
    echo "✅ Generated SSH key"
fi

echo "📋 Copy this public key to your Proxmox host:"
echo "----------------------------------------"
cat "$SSH_DIR/id_rsa.pub"
echo "----------------------------------------"
echo ""
echo "📝 On your Proxmox host, run:"
echo "echo 'KEY_ABOVE' >> /root/.ssh/authorized_keys"
echo ""
echo "🧪 Test connection with:"
echo "sudo -u vmcontroller ssh -i $SSH_DIR/id_rsa root@PROXMOX_IP 'qm list'"
EOF

chmod +x /opt/vm-controller/setup-ssh.sh

echo "=== LXC VM Controller Setup Complete ==="
echo "Files created:"
echo "  - /etc/systemd/system/vm-controller.service"
echo "  - /opt/vm-controller/start.sh"
echo "  - /opt/vm-controller/setup-env.sh"
echo "  - /opt/vm-controller/install.sh"
echo "  - /opt/vm-controller/setup-ssh.sh"