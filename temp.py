from sdncore.vty.session import Session


with Session('50.87.248.237', username='ictshore', password='oven23122+Inuit', driver=Session.SSH, stop_character='# mù',
             driver_parameters={
                 'private_key_file': 'D:\\Software\\Networking\\PuTTY\\id_backup.pem',
                 'private_key_password': 'sFKob!8q_a@q'
             }) as session:
    print(session.command('ls'))

