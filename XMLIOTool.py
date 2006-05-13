# (C) Copyright 2004-2005 Nuxeo SARL <http://nuxeo.com>
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
"""XML-based Import/Export Tool
"""

from zLOG import LOG, ERROR, DEBUG
from Globals import InitializeClass, DTMLFile
from AccessControl import ClassSecurityInfo

from Products.CMFCore.utils import UniqueObject
try:
    from Products.CMFCore.permissions import ManagePortal
except ImportError: # CPS <= 3.2
    from Products.CMFCore.CMFCorePermissions import ManagePortal
from OFS.Folder import Folder

from types import ModuleType
import sys

class XMLIOTool(UniqueObject, Folder):

    id = 'portal_io'
    meta_type = 'CPS IO Tool'

    security = ClassSecurityInfo()

    manage_options = (
        {'label': "Overview",
         'action': 'overview_page'
         },
        ) + Folder.manage_options[2:]

    security.declareProtected(ManagePortal, 'overview_page')
    overview_page = DTMLFile('zmi/overview', globals())

    #
    # Import/export modules management
    #

    def listImportModules(self):
        return self._listPluginNames('import_modules')

    def listExportModules(self):
        return self._listPluginNames('export_modules')

    def _listPluginNames(self, package_name):
        return [ plugin.__name__.split(".")[-1]
                 for plugin in self._listPlugins(package_name) ]

    def _listPlugins(self, package_name):
        dotted_name = "Products.CPSIO." + package_name
        products = __import__(dotted_name)
        package = sys.modules[dotted_name]
        plugin_list = []
        for name in dir(package):
            obj = getattr(package, name)
            if type(obj) == ModuleType:
                plugin_list.append(obj)
        return plugin_list

    def getImportPluginTemplate(self, plugin_name):
        dotted_name = "Products.CPSIO.import_modules.%s" % plugin_name
        products = __import__(dotted_name)
        options_template = sys.modules[dotted_name].Importer.options_template
        if options_template:
            return options_template
        else:
            return "default_importer_form"

    def getImportOptionsTable(self, plugin_name):
        dotted_name = "Products.CPSIO.import_modules.%s" % plugin_name
        products = __import__(dotted_name)
        options_table = sys.modules[dotted_name].Importer.options_table
        return options_table

    def getExportPluginTemplate(self, plugin_name):
        dotted_name = "Products.CPSIO.export_modules.%s" % plugin_name
        products = __import__(dotted_name)
        options_template = sys.modules[dotted_name].Exporter.options_template
        if options_template:
            return options_template
        else:
            return "default_exporter_form"

    def getExportOptionsTable(self, plugin_name):
        dotted_name = "Products.CPSIO.export_modules.%s" % plugin_name
        products = __import__(dotted_name)
        options_table = sys.modules[dotted_name].Exporter.options_table
        return options_table

    def getImportPlugin(self, plugin_name, portal):
        dotted_name = "Products.CPSIO.import_modules.%s" % plugin_name
        products = __import__(dotted_name)
        return sys.modules[dotted_name].Importer(portal).__of__(portal)

    def getExportPlugin(self, plugin_name, portal):
        dotted_name = "Products.CPSIO.export_modules.%s" % plugin_name
        products = __import__(dotted_name)
        return sys.modules[dotted_name].Exporter(portal).__of__(portal)

InitializeClass(XMLIOTool)

