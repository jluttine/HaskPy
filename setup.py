import os
from setuptools import setup, find_packages


if __name__ == "__main__":

    def read(fname):
        return open(os.path.join(os.path.dirname(__file__), fname)).read()

    meta = {}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_dir, 'haskpy', '_meta.py')) as fp:
        exec(fp.read(), meta)

    setup(
        name="haskpy",
        author=meta["__author__"],
        author_email=meta["__contact__"],
        description="Utilities inspired by Haskell and Hask category",
        url="https://github.com/jluttine/HaskPy",
        packages=find_packages(),
        use_scm_version=True,
        setup_requires=[
            "setuptools_scm",
        ],
        install_requires=[
            "attrs",
            "importlib_metadata",
        ],
        extras_require={
            "dev": [
                "pytest",
                "hypothesis",
            ],
            "doc": [
                "sphinx",
            ],
        },
        keywords=[
            "functional programming",
            "category theory",
            "Hask category",
            "Haskell",
            "functor",
            "monad",
        ],
        classifiers=[
            "Programming Language :: Python :: 3 :: Only",
            "Development Status :: 3 - Alpha",
            "Environment :: Console",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: {0}".format(meta["__license__"]),
            "Operating System :: OS Independent",
            "Topic :: Scientific/Engineering",
            "Topic :: Software Development :: Libraries",
        ],
        long_description=read('README.md'),
        long_description_content_type="text/markdown",
    )
