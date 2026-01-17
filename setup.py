from setuptools import setup, find_packages

setup(
    name="SENDUNE_installer",
    version="3.0.11",
    packages=find_packages(),
    # Include non-python files in the package (the assets)
    package_data={
        "SENDUNE_installer": ["assets/*"],
    },
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "senduneinstaller = SENDUNE_installer.__main__:run_as_module",
        ],
    },
    install_requires=[
        'archinstall',
        'pydantic', 
        'pyparted'
    ],
)
