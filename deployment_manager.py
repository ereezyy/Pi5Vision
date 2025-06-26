#!/usr/bin/env python3
"""
Deployment Manager for Pi5 Face Recognition System
Handles remote deployment, configuration management, and updates
"""

import os
import sys
import json
import subprocess
import paramiko
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RemoteHost:
    """Remote host configuration"""
    hostname: str
    username: str
    password: Optional[str] = None
    key_file: Optional[str] = None
    port: int = 22

class DeploymentManager:
    """Manages deployment to remote Raspberry Pi devices"""
    
    def __init__(self):
        self.local_package_dir = Path("dist")
        self.remote_temp_dir = "/tmp/pi5-deployment"
        self.remote_install_dir = "/opt/pi5-face-recognition"
        
    def deploy_to_host(self, host: RemoteHost, package_path: Path) -> bool:
        """Deploy package to remote host"""
        print(f"🚀 Deploying to {host.hostname}...")
        
        try:
            # Establish SSH connection
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if host.key_file:
                ssh.connect(
                    hostname=host.hostname,
                    username=host.username,
                    key_filename=host.key_file,
                    port=host.port
                )
            else:
                ssh.connect(
                    hostname=host.hostname,
                    username=host.username,
                    password=host.password,
                    port=host.port
                )
            
            # Create SFTP client
            sftp = ssh.open_sftp()
            
            # Create remote temp directory
            self._run_ssh_command(ssh, f"mkdir -p {self.remote_temp_dir}")
            
            # Upload package
            remote_package_path = f"{self.remote_temp_dir}/{package_path.name}"
            print(f"📤 Uploading {package_path.name}...")
            sftp.put(str(package_path), remote_package_path)
            
            # Extract package
            print("📦 Extracting package...")
            if package_path.suffix == '.gz':
                extract_cmd = f"cd {self.remote_temp_dir} && tar -xzf {package_path.name}"
            else:
                extract_cmd = f"cd {self.remote_temp_dir} && unzip -o {package_path.name}"
            
            self._run_ssh_command(ssh, extract_cmd)
            
            # Run installer
            package_name = package_path.stem.replace('.tar', '').replace('.zip', '')
            installer_path = f"{self.remote_temp_dir}/{package_name}/install.sh"
            
            print("🔧 Running installer...")
            self._run_ssh_command(ssh, f"chmod +x {installer_path}")
            self._run_ssh_command(ssh, f"sudo {installer_path}")
            
            # Cleanup
            self._run_ssh_command(ssh, f"rm -rf {self.remote_temp_dir}")
            
            # Close connections
            sftp.close()
            ssh.close()
            
            print(f"✅ Deployment to {host.hostname} completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Deployment to {host.hostname} failed: {e}")
            return False
    
    def _run_ssh_command(self, ssh: paramiko.SSHClient, command: str) -> Tuple[int, str, str]:
        """Run command over SSH"""
        stdin, stdout, stderr = ssh.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        stdout_text = stdout.read().decode()
        stderr_text = stderr.read().decode()
        
        if exit_code != 0:
            raise Exception(f"Command failed: {command}\\nError: {stderr_text}")
        
        return exit_code, stdout_text, stderr_text
    
    def check_host_status(self, host: RemoteHost) -> Dict[str, any]:
        """Check status of remote host"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if host.key_file:
                ssh.connect(hostname=host.hostname, username=host.username, key_filename=host.key_file, port=host.port)
            else:
                ssh.connect(hostname=host.hostname, username=host.username, password=host.password, port=host.port)
            
            # Check system info
            _, hostname_out, _ = self._run_ssh_command(ssh, "hostname")
            _, uptime_out, _ = self._run_ssh_command(ssh, "uptime")
            _, disk_out, _ = self._run_ssh_command(ssh, "df -h /")
            _, mem_out, _ = self._run_ssh_command(ssh, "free -h")
            
            # Check if Pi5 Face Recognition is installed
            try:
                _, service_out, _ = self._run_ssh_command(ssh, "systemctl is-active pi5-face-recognition")
                service_status = service_out.strip()
            except:
                service_status = "not-installed"
            
            # Check if web interface is accessible
            try:
                _, curl_out, _ = self._run_ssh_command(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:8080")
                web_status = "online" if curl_out.strip() == "200" else "offline"
            except:
                web_status = "offline"
            
            ssh.close()
            
            return {
                "hostname": hostname_out.strip(),
                "uptime": uptime_out.strip(),
                "disk_usage": disk_out.strip().split('\\n')[1],
                "memory_usage": mem_out.strip().split('\\n')[1],
                "service_status": service_status,
                "web_status": web_status,
                "reachable": True
            }
            
        except Exception as e:
            return {
                "hostname": host.hostname,
                "error": str(e),
                "reachable": False
            }
    
    def bulk_deploy(self, hosts: List[RemoteHost], package_path: Path) -> Dict[str, bool]:
        """Deploy to multiple hosts"""
        print(f"🚀 Starting bulk deployment to {len(hosts)} hosts...")
        
        results = {}
        
        for host in hosts:
            print(f"\\n📡 Deploying to {host.hostname}...")
            success = self.deploy_to_host(host, package_path)
            results[host.hostname] = success
            
            if success:
                print(f"✅ {host.hostname}: SUCCESS")
            else:
                print(f"❌ {host.hostname}: FAILED")
        
        # Summary
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        print(f"\\n📊 Deployment Summary:")
        print(f"  ✅ Successful: {successful}/{total}")
        print(f"  ❌ Failed: {total - successful}/{total}")
        
        return results
    
    def generate_deployment_config(self, hosts: List[RemoteHost], output_file: str = "deployment_config.json") -> None:
        """Generate deployment configuration file"""
        config = {
            "deployment": {
                "version": "1.0",
                "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                "hosts": []
            }
        }
        
        for host in hosts:
            host_config = {
                "hostname": host.hostname,
                "username": host.username,
                "port": host.port,
                "key_file": host.key_file
            }
            config["deployment"]["hosts"].append(host_config)
        
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"📝 Deployment configuration saved to {output_file}")
    
    def load_deployment_config(self, config_file: str = "deployment_config.json") -> List[RemoteHost]:
        """Load deployment configuration"""
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        hosts = []
        for host_config in config["deployment"]["hosts"]:
            host = RemoteHost(
                hostname=host_config["hostname"],
                username=host_config["username"],
                port=host_config.get("port", 22),
                key_file=host_config.get("key_file")
            )
            hosts.append(host)
        
        return hosts

class ConfigurationManager:
    """Manages configuration across multiple deployments"""
    
    def __init__(self):
        self.templates_dir = Path("config_templates")
        self.templates_dir.mkdir(exist_ok=True)
    
    def create_config_template(self, name: str, config: Dict[str, any]) -> None:
        """Create configuration template"""
        template_file = self.templates_dir / f"{name}.json"
        
        with open(template_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"📝 Configuration template '{name}' created")
    
    def apply_config_to_host(self, host: RemoteHost, template_name: str) -> bool:
        """Apply configuration template to remote host"""
        template_file = self.templates_dir / f"{template_name}.json"
        
        if not template_file.exists():
            print(f"❌ Template '{template_name}' not found")
            return False
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if host.key_file:
                ssh.connect(hostname=host.hostname, username=host.username, key_filename=host.key_file, port=host.port)
            else:
                ssh.connect(hostname=host.hostname, username=host.username, password=host.password, port=host.port)
            
            sftp = ssh.open_sftp()
            
            # Upload config file
            remote_config_path = "/opt/pi5-face-recognition/config/config.json"
            sftp.put(str(template_file), remote_config_path)
            
            # Restart service to apply new config
            self._run_ssh_command(ssh, "sudo systemctl restart pi5-face-recognition")
            
            sftp.close()
            ssh.close()
            
            print(f"✅ Configuration applied to {host.hostname}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to apply configuration to {host.hostname}: {e}")
            return False
    
    def _run_ssh_command(self, ssh: paramiko.SSHClient, command: str) -> Tuple[int, str, str]:
        """Run command over SSH"""
        stdin, stdout, stderr = ssh.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        stdout_text = stdout.read().decode()
        stderr_text = stderr.read().decode()
        
        if exit_code != 0:
            raise Exception(f"Command failed: {command}\\nError: {stderr_text}")
        
        return exit_code, stdout_text, stderr_text

def main():
    """Main function for deployment management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pi5 Face Recognition Deployment Manager")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy to remote hosts')
    deploy_parser.add_argument('--package', required=True, help='Package file to deploy')
    deploy_parser.add_argument('--host', required=True, help='Target hostname or IP')
    deploy_parser.add_argument('--user', default='pi', help='SSH username')
    deploy_parser.add_argument('--key', help='SSH key file')
    deploy_parser.add_argument('--password', help='SSH password')
    
    # Bulk deploy command
    bulk_parser = subparsers.add_parser('bulk-deploy', help='Deploy to multiple hosts')
    bulk_parser.add_argument('--package', required=True, help='Package file to deploy')
    bulk_parser.add_argument('--config', required=True, help='Deployment configuration file')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check host status')
    status_parser.add_argument('--host', required=True, help='Target hostname or IP')
    status_parser.add_argument('--user', default='pi', help='SSH username')
    status_parser.add_argument('--key', help='SSH key file')
    status_parser.add_argument('--password', help='SSH password')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Manage configurations')
    config_parser.add_argument('--create', help='Create configuration template')
    config_parser.add_argument('--apply', help='Apply configuration template')
    config_parser.add_argument('--host', help='Target hostname or IP')
    config_parser.add_argument('--user', default='pi', help='SSH username')
    config_parser.add_argument('--key', help='SSH key file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = DeploymentManager()
    config_manager = ConfigurationManager()
    
    if args.command == 'deploy':
        package_path = Path(args.package)
        if not package_path.exists():
            print(f"❌ Package file not found: {package_path}")
            return
        
        host = RemoteHost(
            hostname=args.host,
            username=args.user,
            password=args.password,
            key_file=args.key
        )
        
        manager.deploy_to_host(host, package_path)
    
    elif args.command == 'bulk-deploy':
        package_path = Path(args.package)
        if not package_path.exists():
            print(f"❌ Package file not found: {package_path}")
            return
        
        hosts = manager.load_deployment_config(args.config)
        manager.bulk_deploy(hosts, package_path)
    
    elif args.command == 'status':
        host = RemoteHost(
            hostname=args.host,
            username=args.user,
            password=args.password,
            key_file=args.key
        )
        
        status = manager.check_host_status(host)
        
        print(f"🖥️  Host Status: {args.host}")
        print("=" * 40)
        for key, value in status.items():
            print(f"  {key}: {value}")
    
    elif args.command == 'config':
        if args.create:
            # Create sample configuration
            sample_config = {
                "camera_device": "/dev/video0",
                "resolution": [1280, 720],
                "fps": 30,
                "confidence_threshold": 0.6,
                "web_interface": {
                    "host": "0.0.0.0",
                    "port": 8080
                }
            }
            config_manager.create_config_template(args.create, sample_config)
        
        elif args.apply and args.host:
            host = RemoteHost(
                hostname=args.host,
                username=args.user,
                key_file=args.key
            )
            config_manager.apply_config_to_host(host, args.apply)

if __name__ == "__main__":
    main()