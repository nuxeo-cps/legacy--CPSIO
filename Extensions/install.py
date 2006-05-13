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

"""
CPSIO Installer

HOWTO USE THAT ?

 - Log into the ZMI as manager
 - Go to your CPS root directory
* - Create an External Method with the following parameters:

     id    : cpsIoInstall (or whatever)
     title : CPSIO Installer (or whatever)
     Module Name   :  CPSIO.install
     Function Name : install

 - save it
 - click now the test tab of this external method.
 - that's it !

"""

from Products.CPSInstaller.CPSInstaller import CPSInstaller

def install(self):

    ##############################################
    # Create the installer
    ##############################################
    installer = CPSInstaller(self, 'CPSIO')
    installer.log("Starting CPSIO Install")

    ##############################################
    # Instantiate IOTool
    ##############################################
    if 'portal_io' not in installer.portal.objectIds():
        installer.portal.manage_addProduct['CPSIO'].manage_addTool('CPS IO Tool')

    ##########################################
    # SKINS
    ##########################################
    skins = {'cps_io': 'Products/CPSIO/skins/io_templates',
             'cps_io_plugins': 'Products/CPSIO/skins/io_plugins',}
    installer.verifySkins(skins)
    installer.resetSkinCache()

    ##########################################
    # ACTIONS
    ##########################################
    for aid in ('action_xml_import', 'action_xml_export'):
        portal_actions = installer.portal['portal_actions']
        action_index = installer.getActionIndex(aid, portal_actions)
        if action_index > -1:
            installer.log("Action %s exists, removing for update" % aid)
            portal_actions.deleteActions(selections=(action_index,))
    installer.verifyAction('portal_actions',
                id='action_xml_import',
                name='action_xml_import',
                action="string:${portal_url}/cpsio_importer_chooser",
                permission=('View management screens',),
                category='global',
                visible=1)
    installer.verifyAction('portal_actions',
                id='action_xml_export',
                name='action_xml_export',
                action="string:${portal_url}/cpsio_exporter_chooser",
                permission=('View management screens',),
                category='global',
                visible=1)

    ##############################################
    # i18n support
    ##############################################
    if getattr(installer.portal, 'Localizer', None) is not None:
        installer.setupTranslations()
    else:
        installer.log("Product 'Localizer' not found: translations will not be installed")

    ##############################################
    # Finished!
    ##############################################
    installer.finalize()
    installer.log("End of CPSIO install")
    return installer.logResult()
