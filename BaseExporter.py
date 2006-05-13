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
from Globals import InitializeClass
from AccessControl.Permission import Permission

from Products.CMFCore.utils import UniqueObject
try:
    from Products.CMFCore.permissions import ManagePortal
except ImportError: # CPS <= 3.2
    from Products.CMFCore.CMFCorePermissions import ManagePortal
from AccessControl import ClassSecurityInfo

from zipfile import ZipFile
import re
import shutil

from zLOG import LOG, DEBUG, INFO, WARNING, ERROR

MAIN_NAMESPACE_URI = 'http://www.nuxeo.com/2004/06/'
from Products.CPSIO.IOBase import IOBase

class BaseExporter(UniqueObject, Acquisition.Explicit, IOBase):

    options_template = ''
    options_table = []

    security = ClassSecurityInfo()
    security.declareObjectPublic()

    security.declareProtected(ManagePortal, 'setOptions')
    def setOptions(self, file_name, options=[]):
        """Set export options"""

        file_name = file_name.strip()
        self.archive_file_name = file_name
        self.archive_file_path = os.path.join(CLIENT_HOME, self.archive_file_name)

        self.dir_name = re.sub('.zip', '', file_name)
        self.dir_path = os.path.join(CLIENT_HOME, self.dir_name)
        self.options = options

        # The file_path that corresponds to the main file in the archive, the
        # file that knows where all the other files are.
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name, 'index')

        for file_path in (self.dir_path, self.archive_file_path):
            if os.path.exists(file_path):
                err = "No export will be done because %s exists" % file_path
                LOG('BaseExporter.setOptions', WARNING, err)
                raise ValueError(err)


    security.declareProtected(ManagePortal, 'export')
    def export(self):
        self.init()
        self.exportFile()
        self.finalize()

    security.declareProtected(ManagePortal, 'init')
    def init(self):
        self.log("Export will use dir " + self.dir_path)
        LOG("Export will use dir ", DEBUG, self.dir_path)
        os.makedirs(self.dir_path)

    security.declareProtected(ManagePortal, 'exportFile')
    def exportFile(self):
        """Export the import to the file.

        This is specific to the export plugin.
        """
        raise NotImplementedError

    security.declareProtected(ManagePortal, 'finalize')
    def finalize(self):
        shutil.rmtree(self.dir_path)


    def archiveExport(self):
        # Create a ZipFile object to write into
        archive_file = ZipFile(self.archive_file_path, 'w')
        # walk(path, visit, arg) calls the "visit" function
        # with arguments (arg, dirName, names).
        os.path.walk(self.dir_path, self.archiveFile, archive_file)
        archive_file.close()


    def archiveFile(self, archive_file, dir_name, names):
        for name in names:
            file_path = os.path.join(dir_name, name)
            if not os.path.isdir(file_path):
                file_path_in_archive = re.sub(self.dir_path, self.dir_name, file_path)
                archive_file.write(file_path, file_path_in_archive)

InitializeClass(BaseExporter)

