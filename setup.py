"""Legacy setup.py for editable installs."""
from setuptools import setup, find_packages

setup(
    name="ollacode",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "rich>=13.0.0",
        "prompt_toolkit>=3.0.0",
        "platformdirs>=3.0.0",
        "duckduckgo-search>=4.0.0",
        "chardet>=5.0.0",
    ],
    extras_require={
        "browser": ["playwright>=1.40.0"],
    },
    entry_points={
        "console_scripts": [
            "ollacode=ollacode.main_entry:main",
        ],
    },
)
