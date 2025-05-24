# Proxmox VM Controller

A mobile-friendly web interface for switching between Proxmox VMs with one tap. Perfect for homelab setups where you want to easily switch between gaming and AI/creative workloads.

![VM Controller Interface](https://via.placeholder.com/400x600/667eea/ffffff?text=VM+Controller+Interface)

## 🚀 Features

- 📱 **Mobile-optimized interface** - Works great as a bookmarked "app" on your phone
- 🔄 **One-click VM switching** - Stop one VM and start another with a single tap
- 📊 **Real-time VM status** - See which VMs are running/stopped
- 🔄 **Auto-refresh** - Status updates every 30 seconds
- 🔐 **API key authentication** - Secure access to VM controls
- 🐳 **LXC containerized** - Clean deployment without affecting Proxmox host
- 🔧 **SSH-based control** - Secure communication with Proxmox

## 🎯 Use Cases

Perfect for switching between:
- **Gaming VM** (Windows with GPU passthrough) ↔ **AI/ML VM** (Linux with CUDA)
- **Work VM** ↔ **Media Server VM**
- **Development VM** ↔ **Testing VM**
- Any scenario where you want dedicated GPU/resources for different workloads

## 📋 Prerequisites

- Proxmox VE server
- LXC container capability
- SSH access between container and Proxmox host
- Basic familiarity with Linux command line

## 🛠️ Installation

### 1. Create LXC Container

```bash
# On Proxmox host, create Ubuntu LXC container:
pct create 200 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname vm-controller \
  --memory 512 \
  --cores 1 \
  --rootfs local-lvm:8 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1 \
  --onboot 1

pct start 200
pct enter 200
```

### 2. Install Dependencies

```bash
# Inside the container:
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv openssh-client git

# Create app user
useradd -m -s /bin/bash vmcontroller
```

### 3. Setup Application

```bash
# Create app directory
mkdir -p /opt/vm-controller
cd /opt/vm-controller

# Clone this repository
git clone https://github.com/yourusername/proxmox-vm-controller.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set permissions
chown -R vmcontroller:vmcontroller /opt/vm-controller
```

### 4. Configure SSH Keys

```bash
# Switch to app user
su - vmcontroller

# Generate SSH key
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""

# Display public key to copy to Proxmox host
cat ~/.ssh/id_rsa.pub
```

**On Proxmox host:**
```bash
# Add container's public key to authorized_keys
echo "CONTAINER_PUBLIC_KEY_HERE" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
```

### 5. Configure Application

Edit `/opt/vm-controller/app.py` and update:

```python
PROXMOX_HOST = "192.168.1.100"  # Your Proxmox IP
PROXMOX_USER = "root"
SSH_KEY_PATH = "/home/vmcontroller/.ssh/id_rsa"
API_KEY = "your-secret-api-key-here"  # Change this!

VM_CONFIG = {
    "gaming": {
        "id": 100,  # Your gaming VM ID
        "name": "Gaming VM",
        "description": "Windows gaming virtual machine"
    },
    "ai": {
        "id": 101,  # Your AI/creative VM ID
        "name": "AI/Creative VM", 
        "description": "Linux VM for AI and development"
    }
}
```

### 6. Test and Start

```bash
# Test SSH connection
ssh root@PROXMOX_IP "qm list"

# Start the application
cd /opt/vm-controller
source venv/bin/activate
python app.py
```

## 🔧 Systemd Service (Optional)

To run as a system service:

```bash
# Create startup script
cat > /opt/vm-controller/start.sh << 'EOF'
#!/bin/bash
cd /opt/vm-controller
source venv/bin/activate
exec python app.py
EOF

chmod +x /opt/vm-controller/start.sh

# Create systemd service
cat > /etc/systemd/system/vm-controller.service << 'EOF'
[Unit]
Description=VM Controller API
After=network.target

[Service]
Type=simple
User=vmcontroller
Group=vmcontroller
WorkingDirectory=/opt/vm-controller
ExecStart=/opt/vm-controller/start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable vm-controller
systemctl start vm-controller
```

## 📱 Usage

1. **Access the web interface** at `http://container-ip:5000`
2. **Enter your API key** in the web interface
3. **Bookmark on your phone** for easy access
4. **Tap buttons to switch VMs:**
   - 🎮 "Switch to Gaming" - Stops AI VM, starts Gaming VM
   - 🤖 "Switch to AI/Creative" - Stops Gaming VM, starts AI VM

## 🔒 Security Notes

- Change the default API key in `app.py`
- Consider using HTTPS with a reverse proxy for production
- Restrict container network access if needed
- SSH keys provide secure authentication between container and Proxmox

## 🐛 Troubleshooting

### SSH Connection Issues
```bash
# Test SSH from container
ssh -v root@PROXMOX_IP "qm list"

# Check SSH key permissions
ls -la /home/vmcontroller/.ssh/
```

### Service Issues
```bash
# Check service status
systemctl status vm-controller

# View logs
journalctl -u vm-controller -f
```

### API Issues
```bash
# Test API directly
curl -X POST http://localhost:5000/api/switch \
  -d "target=gaming" \
  -d "api_key=your-api-key"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built for homelab enthusiasts who want simple VM management
- Inspired by the need to easily switch between gaming and AI workloads
- Thanks to the Proxmox and Flask communities

---

**Made with ❤️ for the homelab community**
