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

from zLOG import LOG, DEBUG, INFO, WARNING, ERROR

class IOBase:
    """IOBase: base for importers and exporters

    Used to keep logs while import/export
    """

    messages = []

    #
    # Logging
    #
    def log(self, message):
        self.messages.append(message)

    def flush(self):
        log = '\n'.join(self.messages)
        self.messages = []
        return log

    def logResult(self):
        truc = self.flush()
        return truc
