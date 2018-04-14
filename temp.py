from sdncore.vty.session import Session


with Session('10.0.0.1', username='admin', password='cisco', driver=Session.Telnet, stop_character='>') as session:
    session.command('terminal length 0')
    print(session.command('show run'))
    print(session.command('show ip interface brief'))

