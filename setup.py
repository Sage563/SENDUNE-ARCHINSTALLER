from setuptools import setup, find_packages

setup(
    name="SENDUNE_installer",
    version="0.1",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "SENDUNE_INSTALLER = SENDUNE_installer.full_installation:starting_Sendune",
            "Senduneinstaller = SENDUNE_installer.full_installation:starting_Sendune",
            "senduneinstaller = SENDUNE_installer.full_installation:starting_Sendune",
        ],
    }
)
