# (C) Copyright 2004-2005 Nuxeo SARL <http://nuxeo.com>
# Authors:
# Emmanuel Pietriga <ep@nuxeo.com>
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

from Products.ExternalMethod.ExternalMethod import ExternalMethod
from Products.CPSDefault.tests.CPSTestCase import CPSTestCase, MANAGER_ID

class CPSIOTestCase(CPSTestCase):

    def afterSetUp(self):
        CPSTestCase.afterSetUp(self)
        self.login(MANAGER_ID)
        #portal = getattr(self.app, id)
        #portal.manage_addProduct['CPSIO'].manage_addTool('CPS IO Tool')
        # Then call CPSIO updater
        CPSIO_installer = ExternalMethod('CPSIO_installer',
                                         '', 'CPSIO.install', 'install')
        self.portal._setObject('CPSIO_installer', CPSIO_installer)
        self.portal.CPSIO_installer()
