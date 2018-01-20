from sdncore.vty.drivers.telnet import TelnetDriver

td = TelnetDriver('ictshore.com', port=80)
td.open()
td.send_text('GET /\n')
print(td.read_eof())
