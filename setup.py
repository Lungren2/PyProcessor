from setuptools import setup, find_packages

setup(
    name="pyprocessor",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyQt5>=5.15.0,<6.0.0",
        "tqdm>=4.60.0",
        "darkdetect>=0.8.0",
        "pyqtdarktheme==2.1.0",
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
    python_requires=">=3.6,<3.12",
)
