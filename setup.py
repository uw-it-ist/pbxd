from setuptools import find_packages, setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='pbxd',
    version='1.0.0',
    long_description=readme(),
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=['flask', 'gunicorn', 'pexpect', 'pyte', 'xmltodict'],
)
