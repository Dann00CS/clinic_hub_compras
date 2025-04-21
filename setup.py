from setuptools import setup, find_packages

setup(
    name='clinic_hub_compras', 
    version='0.1.0',
    packages=find_packages(),
    install_requires=[],  # Add dependencies here
    author='Daniel Sierra',
    author_email='sierradaniel.ind@gmail.com',
    description='Python Lib with common functions related with "Proyecto Hub Compras"',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/Dann00CS/clinic_hub_compras',
    classifiers=[
        'Programming Language :: Python :: 3',
    ],
    python_requires='==3.11.11',
)
