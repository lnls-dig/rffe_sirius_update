# RFFE Remote Firmware Update

This script is designed to update all RFFE modules firmware remotely and should be used only in Sirius' BPM system.

The RFFE modules are contained in a isolated network that can only be accessed by the rack's correspondent CPU.
In order to reach them from an outer network, we use SSH Tunneling to redirect the modules ports to a local one.

RFFE IPs in one crate range from 192.168.2.201 to 192.168.2.213 and are mapped to local ports 7001-7013.

## Usage

    ./rffe_sirius_update.py --cfg --version <Firmware version tag> <Firmware binary> <CPU IP List File>

The `--cfg` flag is used to enable the SSH port Forwarding by adding `PermitOpen <RFFE ips>` to `/etc/ssh/sshd_config` in the beggining of the script and reverting it in the end.

The user must provide the IP (or hostname) of the CPUs that have access to the RFFE modules as a file with one CPU info per line, such as:

    IA-01RaBPM-CO-IOCSrv
    IA-02RaBPM-CO-IOCSrv
    ...

The  hostname of all BPM CPUs is provided in the `bpm_cpus` file

### Bootloader update

It's also possible to update the bootloader firmware version by adding the `--bootloader` flag in the script call. Be careful that any problems during the bootloader update will most likely break the boot proccess and make remote communication impossible.

Example:

    ./rffe_sirius_update.py --cfg --bootloader --version <Firmware version tag> <Firmware binary> <CPU IP List File>
