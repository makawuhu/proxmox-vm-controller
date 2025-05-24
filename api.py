#!/usr/bin/env python3
"""
Proxmox VM Controller API
Simple Flask app to control VMs via web interface
"""

from flask import Flask, render_template, jsonify, request
import subprocess
import json
import time
import os
from functools import wraps

app = Flask(__name__)

# Configuration - Update these for your setup
VM_CONFIG = {
    "gaming": {
        "id": 100,
        "name": "Gaming VM",
        "description": "Windows gaming virtual machine"
    },
    "ai": {
        "id": 101, 
        "name": "AI/Creative VM",
        "description": "Linux VM for AI and Stable Diffusion"
    }
}

# Simple API key for basic security (change this!)
API_KEY = "your-secret-api-key-here"

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'POST':
            provided_key = request.headers.get('X-API-Key') or request.form.get('api_key')
            if provided_key != API_KEY:
                return jsonify({"error": "Invalid API key"}), 401
        return f(*args, **kwargs)
    return decorated_function

def run_qm_command(command):
    """Execute qm command and return result"""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
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
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_vm_status(vm_id):
    """Get current status of a VM"""
    result = run_qm_command(f"qm status {vm_id}")
    if result["success"]:
        # Parse status (running, stopped, etc.)
        status = result["output"].split()[-1] if result["output"] else "unknown"
        return status
    return "unknown"

def stop_vm(vm_id):
    """Stop a VM gracefully"""
    return run_qm_command(f"qm shutdown {vm_id}")

def start_vm(vm_id):
    """Start a VM"""
    return run_qm_command(f"qm start {vm_id}")

def force_stop_vm(vm_id):
    """Force stop a VM"""
    return run_qm_command(f"qm stop {vm_id}")

@app.route('/')
def index():
    """Main web interface"""
    return render_template('index.html', vms=VM_CONFIG)

@app.route('/api/status')
def api_status():
    """Get status of all VMs"""
    status = {}
    for vm_type, vm_info in VM_CONFIG.items():
        status[vm_type] = {
            "id": vm_info["id"],
            "name": vm_info["name"],
            "status": get_vm_status(vm_info["id"])
        }
    return jsonify(status)

@app.route('/api/switch', methods=['POST'])
@require_api_key
def api_switch():
    """Switch between VMs"""
    target = request.form.get('target')
    force = request.form.get('force', 'false').lower() == 'true'
    
    if target not in VM_CONFIG:
        return jsonify({"error": "Invalid target VM"}), 400
    
    target_vm = VM_CONFIG[target]
    results = {"steps": [], "success": True}
    
    # Stop all other VMs
    for vm_type, vm_info in VM_CONFIG.items():
        if vm_type != target:
            vm_status = get_vm_status(vm_info["id"])
            if vm_status == "running":
                results["steps"].append(f"Stopping {vm_info['name']}...")
                
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
                    
                # Wait a moment for clean shutdown
                time.sleep(2)
    
    # Start target VM
    target_status = get_vm_status(target_vm["id"])
    if target_status != "running":
        results["steps"].append(f"Starting {target_vm['name']}...")
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

@app.route('/api/control', methods=['POST'])
@require_api_key
def api_control():
    """Control individual VM (start/stop)"""
    vm_type = request.form.get('vm')
    action = request.form.get('action')
    force = request.form.get('force', 'false').lower() == 'true'
    
    if vm_type not in VM_CONFIG:
        return jsonify({"error": "Invalid VM"}), 400
    
    if action not in ['start', 'stop']:
        return jsonify({"error": "Invalid action"}), 400
    
    vm_info = VM_CONFIG[vm_type]
    
    if action == 'start':
        result = start_vm(vm_info["id"])
        message = f"Starting {vm_info['name']}"
    else:  # stop
        if force:
            result = force_stop_vm(vm_info["id"])
            message = f"Force stopping {vm_info['name']}"
        else:
            result = stop_vm(vm_info["id"])
            message = f"Stopping {vm_info['name']}"
    
    if result["success"]:
        return jsonify({"success": True, "message": message})
    else:
        return jsonify({"success": False, "error": result["error"]}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)