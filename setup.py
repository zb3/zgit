from setuptools import setup, find_packages

setup(
    name='zgit',
    version='0.1',
    description='A little tool for uploading stashes',
    url='https://github.com/zb3/zgit',
    author='zb3',
    author_email='sgv@o2.pl',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development',
    ],
    py_modules=['zgit'],
    install_requires = ['zgitignore'],
    entry_points={
        'console_scripts': [
            'zgit=zgit:main',
        ],
    },
)
