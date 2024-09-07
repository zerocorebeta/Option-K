from setuptools import setup, find_packages

# Read the contents of your README file for the long description
with open("README.md", "r") as fh:
    long_description = fh.read()

# Function to parse requirements.txt
def parse_requirements(filename):
    with open(filename, "r") as f:
        lines = f.readlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]

# Parse the requirements
install_requires = parse_requirements("requirements.txt")

setup(
    name="optionk",
    version="1.0.0",
    description="Option-K CLI and server application",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Alex",
    author_email="coredrop@protonmail.com",
    license="MIT",
    packages=find_packages(include=["client", "server"]),
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'opk = client.opk:main',  # Replace `main` with the actual entry point
            'opk-server = server.opk_server:main',  # Replace `main` with the actual entry point
        ],
    },
    # Additional files to include
    package_data={
        'optionk': ['config.ini', 'scripts/*.plist', 'scripts/*.sh'],
    },
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.12',
)
