import setuptools

def readme():
    try:
        with open("README.md") as f:
            return f.read()
    except IOError:
        return ""


setuptools.setup(
    name="psghotkey",
    version="6.0.2",
    author="PySimpleGUI",
    install_requires=["PySimpleGUI","keyboard","psgtray"],
    description="A Hotkey Manager using PySimpleGUI and psgtray",
    long_description=readme(),
    long_description_content_type="text/markdown",
    keywords="GUI UI PySimpleGUI tkinter psghotkey hotkey autohotkey",
    url="https://github.com/PySimpleGUI",
    packages=setuptools.find_packages(),
    license= "GNU Lesser General Public License v3 (LGPLv3)",
    python_requires=">=3.6",
    classifiers=(
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Operating System :: OS Independent",
        "Framework :: PySimpleGUI",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Programming Language :: Python :: 3.15",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Software Development :: User Interfaces",
    ),
    package_data={"":
                      ["*", "*.*","DocstringTools/*"]
                  },
    entry_points={"gui_scripts": [
        "psghotkey=psghotkey.psghotkey:main"
    ], },
)
