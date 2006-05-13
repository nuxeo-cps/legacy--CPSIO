#!/usr/bin/env python
#
# Setup script for the elementtree library
# $Id$
#
# Usage: python setup.py install
#

from distutils.core import setup

try:
    # add download_url syntax to distutils
    from distutils.dist import DistributionMetadata
    DistributionMetadata.download_url = None
except:
    pass

setup(
    name="elementtree",
    version="1.2-20040618",
    author="Fredrik Lundh",
    author_email="fredrik@pythonware.com",
    url="http://effbot.org/zone/element-index.htm",
    download_url="http://effbot.org/downloads#elementtree",
    description="ElementTree - a light-weight XML object model for Python",
    license="Python (BSD style)",
    packages=["elementtree"],
    )
