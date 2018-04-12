from sdncore.sdncore.vty.drivers.ssh import SSHDriver

td = SSHDriver('10.0.0.1', 'admin', 'cisco', shell_mode=True)
td.open()
td.send_text('terminal length 0\n')
td.read_until('#')
td.send_text('show run\n')
print(td.read_until('vty', timeout=20))
td.send_text('show ver\n')
print(td.read_until('#'))
