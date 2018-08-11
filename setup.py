from setuptools import setup


setup(name='sdncore',
      version='0.1.2.dev',
      description='SDN Utils for Python',
      url='https://github.com/alessandromaggio/sdncore',
      author='Alessandro Maggio',
      author_email='me@alessandromaggio.com',
      license='MIT',
      packages=['sdncore'],
      keywords=['SDN', 'ssh', 'telnet', 'network'],
      classifiers=[
            'Development Status :: 3 - Alpha',
            'Programming Language :: Python :: 3'
      ],
      install_requires=['paramiko'],
      zip_safe=False)
