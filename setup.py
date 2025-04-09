from setuptools import setup, find_packages

setup(
    name="video_processor",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyQt5>=5.15.0",
        "tqdm>=4.60.0",
    ],
    entry_points={
        'console_scripts': [
            'video_processor=video_processor.main:main',
        ],
    },
    author="Ethan Ogle",
    author_email="ethanogle012@outlook.com",
    description="Video processing tool for HLS encoding",
    keywords="video, encoding, ffmpeg, hls",
    python_requires=">=3.6",
)
