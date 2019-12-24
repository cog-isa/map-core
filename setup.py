from setuptools import setup

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='mapcore',
    version='1.0.0',
    packages=['mapcore', 'mapcore.swm', 'mapcore.swm.src', 'mapcore.swm.src.components', 'mapcore.planning', 'mapcore.planning', 'mapcore.planning.agent', 'mapcore.planning.grounding',
              'mapcore.planning.parsers', 'mapcore.planning.search'],
    package_dir={'mapcore': 'src'},
    url='https://github.com/glebkiselev/map-core.git',
    license='',
    author='KiselevGA',
    author_email='kiselev@isa.ru',
    long_description=open('README.md').read(),
    install_requires=required,
    include_package_data=True
)