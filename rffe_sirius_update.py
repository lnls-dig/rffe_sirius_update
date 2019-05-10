#!/usr/bin/python
import argparse
from rffe_lib import RFFEControllerBoard
import time
import socket
import paramiko
import getpass
import re
from sshtunnel import SSHTunnelForwarder

rffe_ips = ['192.168.2.'+str(i) for i in range(201, 214)]
rffe_tuple_list = [(ip, 6791) for ip in rffe_ips]
rffe_local_ports = range(7001, 7001+len(rffe_tuple_list))

parser = argparse.ArgumentParser()
parser.add_argument('firmware', type=str, help='New firmware binary file')
parser.add_argument('cpu_list', type=str, help='CPU IP list file')
parser.add_argument('-b','--bootloader', action='store_true', help='The firwmare is a bootloader image')
parser.add_argument('-c','--cfg', action='store_true', default=False, help='Configure CPU SSH port forwarding')
parser.add_argument('-v','--version', default='1_3_0', type=str, help='New firmware version tag')
args = parser.parse_args()

def get_ssh_connection(ssh_machine, ssh_username, ssh_password):
    """Establishes a ssh connection to execute command.
    :param ssh_machine: IP of the machine to which SSH connection to be established.
    :param ssh_username: User Name of the machine to which SSH connection to be established..
    :param ssh_password: Password of the machine to which SSH connection to be established..
    returns connection Object
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ssh_machine, username=ssh_username, password=ssh_password, timeout=10)
    return client

def run_sudo_command(ssh_username="root", ssh_password="abc123", ssh_machine="localhost", command="ls"):
    """Executes a command over a established SSH connection.
    :param ssh_machine: IP of the machine to which SSH connection to be established.
    :param ssh_username: User Name of the machine to which SSH connection to be established..
    :param ssh_password: Password of the machine to which SSH connection to be established..
    returns status of the command executed and Output of the command.
    """
    conn = get_ssh_connection(ssh_machine=ssh_machine, ssh_username=ssh_username, ssh_password=ssh_password)
    command = "sudo -S -p '' %s" % command
    stdin, stdout, stderr = conn.exec_command(command=command)
    stdin.write(ssh_password + "\n")
    stdin.flush()
    stdoutput = [line for line in stdout]
    stderroutput = [line for line in stderr]
    if not stdout.channel.recv_exit_status():
        conn.close()
        if not stdoutput:
            stdoutput = True
        return True, stdoutput
    else:
        conn.close()
        return False, stderroutput

ssh_restart_cmd = 'systemctl restart sshd'
bpm_ioc_stop_cmd = 'systemctl stop halcs-fe@{7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23}'
bpm_ioc_start_cmd = 'systemctl start halcs-fe-ioc@{7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23}'

def TCPForwardConfig(user, pwd, cpu_ip):
    rffe_cfg = [ip+':6791' for ip in rffe_ips]
    cfg_cmd = 'sh -c "echo PermitOpen '+" ".join(rffe_cfg)+' >> /etc/ssh/sshd_config"'

    print('Configuring CPU '+cpu_ip)
    run_sudo_command(user, pwd, cpu_ip, cfg_cmd)
    run_sudo_command(user, pwd, cpu_ip, ssh_restart_cmd)

def TCPForwardRevert(user, pwd, cpu_ip):
    revert_cmd = "sed -i '/PermitOpen/d' /etc/ssh/sshd_config"

    print('Reverting SSH configuration from CPU '+cpu_ip)
    run_sudo_command(user, pwd, cpu_ip, revert_cmd)
    run_sudo_command(user, pwd, cpu_ip, ssh_restart_cmd)

user = getpass.getpass('SSH Username:')
pwd = getpass.getpass('SSH Password:')

#Read all CPU IPs from file
with open(args.cpu_list, 'r') as f:
    cpu_list = [line.rstrip('\n') for line in f]

for cpu_ip in cpu_list:
    if args.cfg:
        #Configure TCP forwarding
        TCPForwardConfig(user, pwd, cpu_ip)
    
    #Stop BPM IOC service
    run_sudo_command(user, pwd, cpu_ip, bpm_ioc_stop_cmd)

    print('Creating RFFE tunnels')
    with SSHTunnelForwarder(
            (cpu_ip, 22),
            mute_exceptions=True,
            ssh_username=user,
            ssh_password=pwd,
            remote_bind_addresses=rffe_tuple_list,
            local_bind_addresses=[('127.0.0.1', port) for port in rffe_local_ports]
    ) as tunnel:
        print('Starting firmware upgrades...')
        for port in rffe_local_ports:
            try:
                rf = RFFEControllerBoard('127.0.0.1', port)
                rf.reprogram(args.firmware, args.version, args.bootloader)
                print('RFFE (port '+str(port)+') successfully updated!')
                rf.close()
            except socket.error as e:
                print('RFFE (port '+str(port)+') not connected! '+str(e))
                continue
            except:
                print('RFFE (port '+str(port)+') failed to update!\n')
                continue

    #Restart BPM IOC service
    run_sudo_command(user, pwd, cpu_ip, bpm_ioc_start_cmd)
    
    if args.cfg:
        #Revert original SSHD configuration
        TCPForwardRevert(user, pwd, cpu_ip)
    
    print('')
