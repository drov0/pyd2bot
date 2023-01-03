from setuptools import setup, find_packages

setup(
    # Application name:
    name="pyd2bot",
    
    # Version number (initial):
    version=open("./VERSION").read(),
    
    # Application author details:
    author="majdoub khalid",
    author_email="majdoub.khalid@gmail.com",
    
    # Packages
    packages=find_packages(),
    
    #Include additional files into the package
    include_package_data=True,
    
    # Details
    url="http://pypi.python.org/pypi/pyd2bot_v100/",
    
    #
    # license="LICENSE.txt",
    description="Light python client for dofus2 offi.",
    
    # long_description=open("README.txt").read(),
    
    # Dependent packages (distributions)
    install_requires=open("./requirements.txt").readlines()
)