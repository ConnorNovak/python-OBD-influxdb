import setuptools

with open("README.md", 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name="python-OBD-influxdb",
    version="0.0.1",
    author="Connor Novak",
    author_email="connor.r.novak@gmail.com",
    description="Python module for logging obd data to InfluxDB",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: Ubuntu",
    ],
    install_requires=[
        'future-fstrings',
        'influxdb',
        'numpy',
        'obd',
        'plac',
    ],
    python_requires='>=3.5',
)
