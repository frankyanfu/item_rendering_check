from setuptools import setup, find_packages

setup(
    name='screenshot-diff',
    version='0.1.0',
    packages=find_packages(),
    python_requires='>=3.9',
    install_requires=[
        'Pillow>=10.0.0',
        'scikit-image>=0.22.0',
        'opencv-python>=4.9.0.0',
        'pytesseract>=0.3.10',
        'imagehash>=4.3.1',
        'numpy>=1.26.0',
        'click>=8.1.0',
    ],
)