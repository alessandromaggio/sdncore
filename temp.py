from sdncore.sdncore.vty.drivers.ssh import SSHDriver

td = SSHDriver('10.0.0.1', 'admin', 'cisco')
td.open()
td.send_text('show run')
print(td.read_until('username'))
