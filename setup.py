import sys
import os
from setuptools import setup

sys.path.append(os.path.join(os.path.dirname(__file__), "coniql"))

from _git_version import get_cmdclass, __version__

# Setup information is stored in setup.cfg but this function call
# is still necessary.
setup(
    cmdclass=get_cmdclass(),
    version=__version__)
