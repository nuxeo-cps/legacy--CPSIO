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

#
# Check ElementTree on the Python if it's not present then link
# ElementTree on the one within CPSIO
#

from zLOG import LOG, INFO, DEBUG

import sys
import os

try:
    import elementtree
except ImportError, e:
    if 'No module named elementtree' not in e:
        raise
    from Products.CPSIO.etree import elementtree
    sys.modules['elementtree'] =  elementtree
    LOG("CPSIO : " ,INFO, "Faking elementtree")


from Products.CMFCore.DirectoryView import registerDirectory
from Products.CMFCore import utils
import XMLIOTool

registerDirectory('skins/io_templates', globals())
registerDirectory('skins/io_plugins', globals())

tools = (
    XMLIOTool.XMLIOTool,
)

def initialize(registrar):
    try:
        utils.ToolInit('CPS IO Tool',
                       tools=tools,
                       icon='tool.png').initialize(registrar)
    except TypeError:
        # BBB for CMF 1.4, remove this in CPS 3.4.0
        utils.ToolInit('CPS IO Tool',
                       tools=tools,
                       product_name='CPSIO', # BBB
                       icon='tool.png').initialize(registrar)
