from setuptools import setup, find_packages

setup(
    name="bitrate-calc",
    version="0.1.1",
    packages=find_packages(),
    install_requires=[
        "pydub==0.25.1",
        "moviepy==2.1.2",
        "numpy==1.26.4",
        "decorator==5.1.1",
        "ffmpeg-python==0.2.0",
    ],
    entry_points={
        "console_scripts":[
            "bitrate-calc = bitrate_calc.cli:main"
        ]
    },
    author="kr4us3r",
    author_email="bakemonowa@gmail.com",
    description="Calculate audio and video bitrates for media files",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/kr4us3r/bitrate-calc",
    license="MIT",
)