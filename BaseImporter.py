# (C) Copyright 2004 Nuxeo SARL <http://nuxeo.com>
# Author: Emmanuel Pietriga <ep@nuxeo.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
# 02111-1307, USA.
#
# $Id$

import os, random

import Acquisition
from Acquisition import aq_base
from Globals import InitializeClass
from AccessControl.Permission import Permission

from Products.CMFCore.utils import UniqueObject
from Products.CMFCore.permissions import ManagePortal
from AccessControl import ClassSecurityInfo

from elementtree.ElementTree import ElementTree, Element, SubElement

from zipfile import ZipFile
from zipfile import is_zipfile
import re      # for Perl-style regular expression operations
import shutil

from types import ListType

from zLOG import LOG, DEBUG, INFO, WARNING, ERROR

MAIN_NAMESPACE_URI = 'http://www.nuxeo.com/2004/06/'
from Products.CPSIO.IOBase import IOBase

class BaseImporter(UniqueObject, Acquisition.Explicit, IOBase):

    options_template = ''
    options_table = []

    security = ClassSecurityInfo()
    security.declareObjectPublic()

    security.declareProtected(ManagePortal, 'setOptions')
    def setOptions(self, file_name, options=[]):
        """Set import options

        The zip archive has to be given in the 'import' directory.
        """
        file_name = file_name.strip()
        file_path = os.path.join(INSTANCE_HOME, 'import', file_name)

        if not os.path.isfile(file_path):
            err = ("File %s does not exist. "
                   "Check that your file is in the Zope import directory."
                   % file_path)
            LOG('BaseImporter.setOptions', WARNING, err)
            raise ValueError(err)

        if not is_zipfile(file_path):
            err = "File %s is not a ZIP archive." % file_path
            LOG('BaseImporter.setOptions', WARNING, err)
            raise ValueError(err)

        self.unzipArchive(file_path)

        self.dir_name = re.sub('.zip', '', file_name)
        self.dir_path = os.path.join(CLIENT_HOME, self.dir_name)
        self.options = options

        self.file_path = os.path.join(CLIENT_HOME, self.dir_name, 'index')


    security.declareProtected(ManagePortal, 'finalize')
    def finalize(self):
        shutil.rmtree(self.dir_path)


    security.declareProtected(ManagePortal, 'unzipArchive')
    def unzipArchive(self, file_path):
        """The archive is unpacked in the var directory."""
        self.log("Unziping archive file_path = %s" % file_path)
        LOG('BaseImporter.unzipArchive', DEBUG, "file_path = %s" % file_path)
        # Uncompress zipfile into a flat structure
        archive_file = ZipFile(file_path)
        for entry_name in archive_file.namelist():
            LOG('BaseImporter.unzipArchive', DEBUG,
                "entry_name = %s" % entry_name)
            entry_file_path = os.path.join(CLIENT_HOME, entry_name)
            LOG('BaseImporter.unzipArchive', DEBUG,
                "entry_file_path = %s" % entry_file_path)
            try:
                os.makedirs(os.path.dirname(entry_file_path))
            except OSError:
                pass
            fstr = archive_file.read(entry_name)
            f = open(entry_file_path, 'w')
            f.write(fstr)
            f.close()
            del fstr
        archive_file.close()

InitializeClass(BaseImporter)

