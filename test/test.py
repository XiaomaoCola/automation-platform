from platform import python_version

hosts = {
    "Kali": {"ip": "192.168.50.101", "user": "zrs"},
    "VPN-VM": {"ip": "192.168.50.201", "user": "zrs"},
}

for name, info in hosts.items():
    print(name)
    print(info)


print(python_version())