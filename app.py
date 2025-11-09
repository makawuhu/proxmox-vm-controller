#!/usr/bin/env python3
"""
Proxmox VM Controller
Mobile-friendly web interface for switching between Proxmox VMs
"""

import os
import json
import subprocess
import time
import secrets
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# --- Configuration ---
CONFIG_FILE = "config.json"
config = {}

def first_run_setup():
    """Prompt user for configuration and save to file."""
    print("--- First Time Setup ---")
    
    config_data = {}
    config_data["PROXMOX_HOST"] = input("Enter Proxmox Host IP: ")
    config_data["PROXMOX_USER"] = input("Enter Proxmox SSH User (e.g., root): ")
    config_data["SSH_KEY_PATH"] = input("Enter path to SSH private key (e.g., /home/user/.ssh/id_rsa): ")
    config_data["API_KEY"] = secrets.token_hex(16)
    print(f"Generated API Key: {config_data['API_KEY']}")
    
    config_data["VM_CONFIG"] = {}
    while True:
        add_vm = input("Add a VM? (y/n): ").lower()
        if add_vm != 'y':
            break
        
        vm_key = input("Enter a short name for the VM (e.g., 'gaming', 'ai'): ")
        vm_id = int(input(f"Enter VM ID for '{vm_key}': "))
        vm_name = input(f"Enter a display name for '{vm_key}': ")
        vm_desc = input(f"Enter a description for '{vm_key}': ")
        
        config_data["VM_CONFIG"][vm_key] = {
            "id": vm_id,
            "name": vm_name,
            "description": vm_desc
        }
        
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)
        
    print(f"\nConfiguration saved to {CONFIG_FILE}")

def load_config():
    """Load configuration from file."""
    global config
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)

def save_config(new_config):
    """Save configuration to file."""
    global config
    with open(CONFIG_FILE, 'w') as f:
        json.dump(new_config, f, indent=4)
    config = new_config

def run_ssh_command(command):
    """Execute command on Proxmox host via SSH"""
    ssh_command = [
        "ssh", 
        "-i", config["SSH_KEY_PATH"],
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=10",
        "-o", "BatchMode=yes",
        f"{config['PROXMOX_USER']}@{config['PROXMOX_HOST']}",
        command
    ]
    
    try:
        result = subprocess.run(
            ssh_command,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip()
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "SSH command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_connection():
    """Test SSH connection to Proxmox host"""
    result = run_ssh_command("qm list")
    return result["success"]

def get_vm_status(vm_id):
    """Get current status of a VM"""
    result = run_ssh_command(f"qm status {vm_id}")
    if result["success"]:
        status = result["output"].split()[-1] if result["output"] else "unknown"
        return status
    return "unknown"

def stop_vm(vm_id):
    """Stop a VM gracefully"""
    return run_ssh_command(f"qm shutdown {vm_id}")

def start_vm(vm_id):
    """Start a VM"""
    return run_ssh_command(f"qm start {vm_id}")

def force_stop_vm(vm_id):
    """Force stop a VM"""
    return run_ssh_command(f"qm stop {vm_id}")

@app.route('/')
def index():
    """Main web interface"""
    return render_template('index.html', vms=config.get("VM_CONFIG", {}))

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html')

@app.route('/manifest.json')
def manifest():
    """PWA manifest file"""
    return {
        "name": "VM Controller",
        "short_name": "VM Controller", 
        "description": "Control Proxmox VMs from your phone",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#667eea",
        "theme_color": "#667eea",
        "orientation": "portrait",
        "scope": "/",
        "icons": [
            {
                "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' fill='%23667eea'/><text x='50' y='60' text-anchor='middle' fill='white' font-size='40' font-family='Arial'>🖥️</text></svg>",
                "sizes": "192x192",
                "type": "image/svg+xml",
                "purpose": "any maskable"
            },
            {
                "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' fill='%23667eea'/><text x='50' y='60' text-anchor='middle' fill='white' font-size='60' font-family='Arial'>🖥️</text></svg>",
                "sizes": "512x512", 
                "type": "image/svg+xml",
                "purpose": "any maskable"
            }
        ]
    }

@app.route('/api/status')
def api_status():
    """Get status of all VMs"""
    if not test_connection():
        return jsonify({"error": "Cannot connect to Proxmox host"}), 500
    
    status = {}
    for vm_type, vm_info in config.get("VM_CONFIG", {}).items():
        status[vm_type] = {
            "id": vm_info["id"],
            "name": vm_info["name"],
            "status": get_vm_status(vm_info["id"])
        }
    return jsonify(status)

@app.route('/api/get_settings')
def get_settings():
    """Get current configuration"""
    api_key = request.headers.get('X-API-Key')
    if api_key != config.get("API_KEY"):
        return jsonify({"error": "Invalid API key"}), 401
    return jsonify(config)

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update configuration"""
    api_key = request.headers.get('X-API-Key')
    if api_key != config.get("API_KEY"):
        return jsonify({"error": "Invalid API key"}), 401
        
    new_config_data = request.json
    
    # Basic validation
    if not all(k in new_config_data for k in ["proxmox_host", "proxmox_user", "ssh_key_path", "vm_config"]):
        return jsonify({"error": "Missing required fields"}), 400
        
    # Construct the new config object
    updated_config = {
        "PROXMOX_HOST": new_config_data["proxmox_host"],
        "PROXMOX_USER": new_config_data["proxmox_user"],
        "SSH_KEY_PATH": new_config_data["ssh_key_path"],
        "API_KEY": new_config_data.get("api_key") or config.get("API_KEY"),
        "VM_CONFIG": new_config_data["vm_config"]
    }
    
    save_config(updated_config);
    
    return jsonify({"success": True, "message": "Settings updated successfully"})

@app.route('/api/switch', methods=['POST'])
def api_switch():
    """Switch between VMs"""
    try:
        # Check API key
        api_key = request.headers.get('X-API-Key') or request.form.get('api_key')
        if api_key != config.get("API_KEY"):
            return jsonify({"error": "Invalid API key"}), 401
        
        target = request.form.get('target')
        force = request.form.get('force', 'false').lower() == 'true'
        
        print(f"Switch request for: {target}")
        
        vm_config = config.get("VM_CONFIG", {})
        if target not in vm_config:
            return jsonify({"error": "Invalid target VM"}), 400
        
        if not test_connection():
            return jsonify({"error": "Cannot connect to Proxmox host"}), 500
        
        target_vm = vm_config[target]
        results = {"steps": [], "success": True}
        
        # Stop all other VMs
        for vm_type, vm_info in vm_config.items():
            if vm_type != target:
                vm_status = get_vm_status(vm_info["id"])
                if vm_status == "running":
                    results["steps"].append(f"Stopping {vm_info['name']}...")
                    print(f"Stopping VM {vm_info['id']}")
                    
                    if force:
                        result = force_stop_vm(vm_info["id"])
                    else:
                        result = stop_vm(vm_info["id"])
                    
                    if not result["success"]:
                        results["success"] = False
                        results["steps"].append(f"Failed to stop {vm_info['name']}: {result['error']}")
                        return jsonify(results), 500
                    else:
                        results["steps"].append(f"Stopped {vm_info['name']}")
                        
                    # Wait for clean shutdown
                    time.sleep(3)
        
        # Start target VM
        target_status = get_vm_status(target_vm["id"])
        if target_status != "running":
            results["steps"].append(f"Starting {target_vm['name']}...")
            print(f"Starting VM {target_vm['id']}")
            result = start_vm(target_vm["id"])
            
            if not result["success"]:
                results["success"] = False
                results["steps"].append(f"Failed to start {target_vm['name']}: {result['error']}")
                return jsonify(results), 500
            else:
                results["steps"].append(f"Started {target_vm['name']}")
        else:
            results["steps"].append(f"{target_vm['name']} was already running")
        
        return jsonify(results)
        
    except Exception as e:
        print(f"Error in api_switch: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists(CONFIG_FILE):
        first_run_setup()
    
    load_config()
    
    # Verify SSH connection on startup
    print("Testing SSH connection to Proxmox host...")
    if test_connection():
        print("✅ Connection successful!")
    else:
        print("❌ Cannot connect to Proxmox host. Check SSH configuration.")
        print(f"Host: {config.get('PROXMOX_HOST')}")
        print(f"User: {config.get('PROXMOX_USER')}")
        print(f"SSH Key: {config.get('SSH_KEY_PATH')}")
    
    # Run the app
    app.run(host='0.0.0.0', port=5001, debug=True)
