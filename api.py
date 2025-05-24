#!/usr/bin/env python3
"""
Proxmox VM Controller
Mobile-friendly web interface for switching between Proxmox VMs
"""

from flask import Flask, render_template, jsonify, request
import subprocess
import time

app = Flask(__name__)

# Configuration - Update these for your setup
PROXMOX_HOST = "192.168.4.10"
PROXMOX_USER = "root"
SSH_KEY_PATH = "/home/vmcontroller/.ssh/id_rsa"
API_KEY = "your-secret-api-key-here"

VM_CONFIG = {
    "gaming": {
        "id": 100,  # win11enterprise - Windows gaming VM
        "name": "Gaming VM (Windows 11)",
        "description": "Windows 11 Enterprise gaming VM"
    },
    "ai": {
        "id": 108,  # openwebui - AI/Creative VM
        "name": "AI/Creative VM (OpenWebUI)",
        "description": "VM for AI and Stable Diffusion"
    }
}

def run_ssh_command(command):
    """Execute command on Proxmox host via SSH"""
    ssh_command = [
        "ssh", 
        "-i", SSH_KEY_PATH,
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=10",
        "-o", "BatchMode=yes",
        f"{PROXMOX_USER}@{PROXMOX_HOST}",
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
    return render_template('index.html', vms=VM_CONFIG)

@app.route('/api/status')
def api_status():
    """Get status of all VMs"""
    if not test_connection():
        return jsonify({"error": "Cannot connect to Proxmox host"}), 500
    
    status = {}
    for vm_type, vm_info in VM_CONFIG.items():
        status[vm_type] = {
            "id": vm_info["id"],
            "name": vm_info["name"],
            "status": get_vm_status(vm_info["id"])
        }
    return jsonify(status)

@app.route('/api/switch', methods=['POST'])
def api_switch():
    """Switch between VMs"""
    try:
        # Check API key
        api_key = request.headers.get('X-API-Key') or request.form.get('api_key')
        if api_key != API_KEY:
            return jsonify({"error": "Invalid API key"}), 401
        
        target = request.form.get('target')
        force = request.form.get('force', 'false').lower() == 'true'
        
        print(f"Switch request for: {target}")
        
        if target not in VM_CONFIG:
            return jsonify({"error": "Invalid target VM"}), 400
        
        if not test_connection():
            return jsonify({"error": "Cannot connect to Proxmox host"}), 500
        
        target_vm = VM_CONFIG[target]
        results = {"steps": [], "success": True}
        
        # Stop all other VMs
        for vm_type, vm_info in VM_CONFIG.items():
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
    # Verify SSH connection on startup
    print("Testing SSH connection to Proxmox host...")
    if test_connection():
        print("✅ Connection successful!")
    else:
        print("❌ Cannot connect to Proxmox host. Check SSH configuration.")
        print(f"Host: {PROXMOX_HOST}")
        print(f"User: {PROXMOX_USER}")
        print(f"SSH Key: {SSH_KEY_PATH}")
    
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)
