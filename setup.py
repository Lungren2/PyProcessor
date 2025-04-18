from setuptools import setup, find_packages

setup(
    name="pyprocessor",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "tqdm>=4.60.0",
    ],
    entry_points={
        "console_scripts": [
            "pyprocessor=pyprocessor.main:main",
        ],
    },
    author="Ethan Ogle",
    author_email="ethanogle012@outlook.com",
    description="Video processing tool for HLS encoding",
    keywords="video, encoding, ffmpeg, hls",
    python_requires=">=3.6,<3.14",
)
