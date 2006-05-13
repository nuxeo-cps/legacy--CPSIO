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

from Globals import InitializeClass

from Products.CMFCore.permissions import ManagePortal
from Products.CPSIO.BaseExporter import BaseExporter
from Products.CPSIO.IOBase import IOBase

from AccessControl import ClassSecurityInfo

from elementtree.ElementTree import ElementTree, Element, SubElement

import os
from types import ListType, TupleType

from zLOG import LOG, DEBUG, INFO, WARNING, ERROR

MAIN_NAMESPACE_URI = 'http://www.nuxeo.com/2004/06/'

class Exporter(BaseExporter):

    options_template = 'plone2exporter_form'

    security = ClassSecurityInfo()
    security.declareObjectPublic()

    __roles__ = None
    __allow_access_to_unprotected_subobjects__ = 1

    def __init__(self, portal):
        self.portal = portal
        self.ns_uri = MAIN_NAMESPACE_URI + 'cps3#'

    security.declareProtected(ManagePortal, 'export')
    def exportFile(self):
        """Main Export"""

        self.log("Exporting to file " + self.file_path)
        LOG("Exporting to file ", DEBUG, self.file_path)
        root = self.buildTree()
        if 'export_portal_types' in self.options:
            file_name = PortalTypeExporter(self.portal, self.dir_name).exportFile()
            el = SubElement(root, "{%s}cpsportaltypes" % self.ns_uri)
            el.set('ref', file_name)
        if 'export_workflows' in self.options:
            file_name = WorkflowExporter(self.portal, self.dir_name).exportFile()
            el = SubElement(root, "{%s}cpsworkflows" % self.ns_uri)
            el.set('ref', file_name)
        if ('export_hierarchy' in self.options or
            'export_documents' in self.options):
            ehms = [item for item in self.options if item.startswith('export_hierarchy_')]
            if ehms:
                ehm = ehms[0][17:]
            else:
                ehm = None
            file_name = HierarchyExporter(self.portal, self.dir_name, ehm).exportFile()
            el = SubElement(root, "{%s}cpshierarchy" % self.ns_uri)
            el.set('ref', file_name)
        doc = ElementTree(root)
        doc.write(self.file_path, encoding="iso-8859-15")

        self.archiveExport()

    def buildTree(self):
        root = Element("{%s}cpsdefinitions" % self.ns_uri)
        return root


InitializeClass(Exporter)

#
# CMF/Plone 2 Portal Type Exporter
#
class PortalTypeExporter(IOBase):

    def __init__(self, portal, dir_name):
        self.portal = portal
        self.pt_tool = self.portal.portal_types
        self.file_name = 'portal_types'
        self.file_path = os.path.join(CLIENT_HOME, dir_name, self.file_name)
        self.ns_uri = MAIN_NAMESPACE_URI + 'cpsportaltypes#'

    def exportFile(self):
        """Export portal types"""

        self.log("Exporting portal types to file " + self.file_path)
        LOG("Exporting portal types to file", DEBUG, self.file_path)

        root = self.buildTree()
        doc = ElementTree(root)
        doc.write(self.file_path, encoding="iso-8859-15")
        return self.file_name

    def buildTree(self):
        """Build the elementtree representing all FTIs"""

        root = Element("{%s}portalTypes" % self.ns_uri)

        for pt_id, pt in self.pt_tool.objectItems():
            el = self.exportCMFFTI(pt_id, pt, root)

        return root

    def exportCMFFTI(self, pt_id, fti, parent):
        """Build an elementtree representation of a Factory-based Type
        Information object"""

        el = SubElement(parent, "{%s}cmffti" % self.ns_uri)
        el.set('id', pt_id)
        # process properties
        for prop in self._getFTIProperties(fti):
            # export some properties as attributes
            if prop[0] in ('content_icon', 'content_meta_type', 'product',
                           'factory', 'immediate_view', 'global_allow',
                           'filter_content_types', 'allow_discussion'):
                if prop[1] is not None:
                    el.set(prop[0], str(prop[1]))
                else:
                    el.set(prop[0], '')
            # export all other as elements - this includes the ones
            # we do not know anything about
            else:
                el2 = SubElement(el, "{%s}%s" % (self.ns_uri, prop[0]))
                if isinstance(prop[1], ListType) or isinstance(prop[1], TupleType):
                    el2.text = ','.join([token for token in prop[1]])
                else:
                    el2.text = str(prop[1])
                el2.set('type', type(prop[1]).__name__)

        # process actions
        self.exportActions(fti, el)
        return el

    def exportActions(self, fti, parent):
        """Process actions associated with an FTI"""

        el = SubElement(parent, "{%s}actions" % self.ns_uri)
        for action in self._getActions(fti):
            el2 = SubElement(el, "{%s}action" % self.ns_uri)
            el2.set('id', action.getId())
            el2.set('name', action.Title())
            el2.set('category', action.getCategory())
            if action.getVisibility():
                el2.set('visibility', '1')
            else:
                el2.set('visibility', '0')
            el3 = SubElement(el2, "{%s}expression" % self.ns_uri)
            el3.text = action.getActionExpression()
            if action.getCondition():
                el3 = SubElement(el2, "{%s}condition" % self.ns_uri)
                el3.text = action.getCondition()
            perms = action.getPermissions()
            if len(perms) and perms[0]:
                # no permissions <=> perms = ('',)
                el3 = SubElement(el2, "{%s}permission" % self.ns_uri)
                el3.text = ','.join([token for token in action.getPermissions()])

    def _getFTIProperties(self, fti):
        """Get all properties of a given FTI"""

        return fti.propertyItems()

    def _getActions(self, fti):
        """Get action definitions (python ds)"""

        return fti.listActions()

#
# CMF/Plone 2 Workflow Exporter
#
class WorkflowExporter(IOBase):

    def __init__(self, portal, dir_name):
        self.portal = portal
        self.wtool = self.portal.portal_workflow
        self.pt_tool = self.portal.portal_types
        self.file_name = 'workflows'
        self.file_path = os.path.join(CLIENT_HOME, dir_name, self.file_name)
        self.ns_uri = MAIN_NAMESPACE_URI + 'cpsworkflows#'

    def exportFile(self):
        """Export workflows"""

        self.log("Exporting workflows to file " + self.file_path)
        LOG("Exporting workflows to file", DEBUG, self.file_path)

        root = self.buildTree()
        doc = ElementTree(root)
        doc.write(self.file_path, encoding="iso-8859-15")
        return self.file_name

    def buildTree(self):
        """Build the elementtree representing all workflows"""

        root = Element("{%s}workflows" % self.ns_uri)

        # first, get chains at the portal_work level
        el = SubElement(root, "{%s}globalChains" % self.ns_uri)
        for portal_type in self.pt_tool.objectIds():
            chain = list(self.wtool.getChainFor(portal_type))
            if chain:
                el2 = SubElement(el, "{%s}globalChain" % self.ns_uri)
                el2.set('chain', ','.join(chain))
                el2.set('portal_type', portal_type)

        el = SubElement(root, "{%s}workflowDefinitions" % self.ns_uri)
        for wf_id, wf in self.wtool.objectItems():
            self.buildWorkflow(wf_id, wf, el)
        # provide trigger type mapping in case constant values change
        # in the code
        el = SubElement(root, "{%s}triggerTypes" % self.ns_uri)
        from Products.DCWorkflow import Transitions
        for trigger_type in [attr for attr in Transitions.__dict__.keys()
                             if attr.startswith('TRIGGER_')]:
            el2 = SubElement(el, "{%s}triggerType" % self.ns_uri)
            el2.set('name', trigger_type)
            el2.set('ref', str(getattr(Transitions, trigger_type)))
        # there are no transition behaviors in CMF/Plone, but this
        # is a required element of the relax-ng schema
        el = SubElement(root, "{%s}transitionBehaviors" % self.ns_uri)
        return root

    def buildWorkflow(self, wf_id, workflow, parent):
        """Build an elementtree representation of a workflow"""

        el = SubElement(parent, "{%s}workflow" % self.ns_uri)
        el.set('id', wf_id)
        el.set('title', workflow.title)
        if workflow.state_var:
            el.set('state_variable', workflow.state_var)
        if workflow.permissions:
            el.set('permissions', ','.join(list(workflow.permissions)))

        self.buildStates(workflow.states.objectValues(), el)
        self.buildTransitions(workflow.transitions.objectValues(), el)
        self.buildScripts(workflow.scripts.objectValues(), el)
        self.buildVariables(workflow.variables.objectValues(), el)

    def buildStates(self, states, parent):
        """Build an elementtree representation of a workflow's states"""

        el = SubElement(parent, "{%s}states" % self.ns_uri)
        for state in states:
            el2 = SubElement(el, "{%s}state" % self.ns_uri)
            el2.set('id', state.id)
            el2.set('title', state.title)
            el2.set('description', state.description)
            if state.transitions:
                el2.set('allowedTransitions', ','.join(list(state.transitions)))
            if state.permissions:
                el3 = SubElement(el2, "{%s}permissions" % self.ns_uri)
                for permission in state.permissions:
                    el4 = SubElement(el3, "{%s}permission" % self.ns_uri)
                    el4.set('title', permission)
                    perm_info = state.getPermissionInfo(permission)
                    el4.set('acquired', str(perm_info.get('acquired', 1)))
                    roles = perm_info.get('roles', [])
                    if roles:
                        el4.set('roles', ','.join(roles))
            if state.var_values:
                el3 = SubElement(el2, "{%s}variableValues" % self.ns_uri)
                for var_name, var_value in state.var_values.items():
                    el4 = SubElement(el3, "{%s}variableValue" % self.ns_uri)
                    el4.set('name', str(var_name))
                    el4.set('value', str(var_value))
                    el4.set('type', type(var_value).__name__)

    def buildTransitions(self, transitions, parent):
        """Build an elementtree representation of a workflow's transitions"""

        el = SubElement(parent, "{%s}transitions" % self.ns_uri)

        for transition in transitions:
            el2 = SubElement(el, "{%s}transition" % self.ns_uri)
            el2.set('id',transition.getId())
            # DCWorkflow Transition data
            el2.set('title', transition.title)
            el2.set('description', transition.description)
            el2.set('new_state_id', transition.new_state_id)
            # trigger_type is an int
            el2.set('trigger_type', str(transition.trigger_type))
            if transition.actbox_name:
                el2.set('actbox_name', transition.actbox_name)
            if transition.actbox_url:
                el2.set('actbox_url', transition.actbox_url)
            if transition.actbox_category:
                el2.set('actbox_category', transition.actbox_category)
            if transition.script_name:
                el2.set('script_name', transition.script_name)
            if transition.after_script_name:
                el2.set('after_script_name', transition.after_script_name)
            guard = transition.getGuard()
            g_permissions = guard.getPermissionsText()
            g_roles = guard.getRolesText()
            g_expression = guard.getExprText()
            if g_permissions or g_roles or g_expression:
                el3 = SubElement(el2, "{%s}guard" % self.ns_uri)
                if g_permissions:
                    el3.set('permissions', g_permissions)
                if g_roles:
                    el3.set('roles', g_roles)
                if g_expression:
                    el3.set('expr', g_expression)

    def buildScripts(self, scripts, parent):
        """Build an elementtree representation of a workflow's scripts"""

        el = SubElement(parent, "{%s}scripts" % self.ns_uri)
        for script in scripts:
            el2 = SubElement(el, "{%s}script" % self.ns_uri)
            el2.set('id', script.id)
            el2.set('title', script.title)
            # get script code, remove lines starting with ##bind (not necessary)
            code = script.read()
            code_lines = code.splitlines(1)
            code_lines = [line for line in code_lines if not line.startswith('##bind')]
            code = ''.join(code_lines)
            el3 = SubElement(el2, "{%s}code" % self.ns_uri)
            el3.set('xml:space', 'preserve')
            el3.text = code
            if getattr(script, '_proxy_roles', None):
                el2.set('proxy_roles', ','.join(list(script._proxy_roles)))
            if getattr(script, '_owner', None):
                el2.set('owner', str(script._owner))

    def buildVariables(self, variables, parent):
        """Build an elementtree representation of a workflow's variables"""

        el = SubElement(parent, "{%s}variables" % self.ns_uri)
        for variable in variables:
            el2 = SubElement(el, "{%s}variable" % self.ns_uri)
            el2.set('id', variable.id)
            el2.set('description', variable.description)
            if variable.for_catalog:
                el2.set('availableToCatalog', '1')
            else:
                el2.set('availableToCatalog', '0')
            if variable.for_status:
                el2.set('storeInWorkflowStatus', '1')
            else:
                el2.set('storeInWorkflowStatus', '0')
            if variable.default_value:
                el3 = SubElement(el2, "{%s}defaultValue" % self.ns_uri)
                el3.text = variable.default_value
            det = variable.getDefaultExprText()
            if det:
                el3 = SubElement(el2, "{%s}defaultExpression" % self.ns_uri)
                el3.text = det
            if variable.update_always:
                el2.set('always_update', '1')
            else:
                el2.set('always_update', '0')
            guard = variable.getInfoGuard()
            g_permissions = guard.getPermissionsText()
            g_roles = guard.getRolesText()
            g_expression = guard.getExprText()
            if g_permissions or g_roles or g_expression:
                el3 = SubElement(el2, "{%s}guard" % self.ns_uri)
                if g_permissions:
                    el3.set('permissions', g_permissions)
                if g_roles:
                    el3.set('roles', g_roles)
                if g_expression:
                    el3.set('expr', g_expression)

#
# CMF/Plone 2 Hierarchy Exporter
#
class HierarchyExporter(IOBase):

    def __init__(self, portal, dir_name, export_hierarchy_method):
        self.portal = portal
        self.mtool = self.portal.portal_membership
        self.file_name = 'hierarchy'
        self.file_path = os.path.join(CLIENT_HOME, dir_name, self.file_name)
        self.ns_uri = MAIN_NAMESPACE_URI + 'cpshierarchy#'
        # should be wssc, ws or sc
        self.export_hierarchy_method = export_hierarchy_method

    def exportFile(self):
        """Export hierarchy"""

        self.log("Exporting hierarchy to file " + self.file_path)
        LOG("Exporting hierarchy to file", DEBUG, self.file_path)

        root = self.buildTree()
        doc = ElementTree(root)
        doc.write(self.file_path, encoding="utf-8")
        return self.file_name

    def buildTree(self):
        """Build the elementtree representing hierarchy"""

        root = Element("{%s}hierarchy" % self.ns_uri)

        if self.export_hierarchy_method in ('wssc', 'ws'):
            ws_el = self.createFolder('workspaces', 'Workspace', root,
                                      {'title': 'Workspaces'},
                                      {'Title': 'Workspaces'})

        if self.export_hierarchy_method in ('wssc', 'sc'):
            sc_el = self.createFolder('sections', 'Section', root,
                                      {'title': 'Sections'},
                                      {'Title': 'Sections'})
        
        # get all CMF/Plone hierarchy elements which are direct children
        # of the portal object (typically Members/ and other folders)
        # and do a recursive descent of the tree
        for object in self.portal.objectValues():
            if object.meta_type in ('Plone Folder', 'Large Plone Folder',
                                    'Folder'):
                if self.export_hierarchy_method in ('wssc', 'ws'):
                    self.buildFolder(object, ws_el, 'Workspace')
                if (self.export_hierarchy_method in ('wssc', 'sc')
                    and object.id != 'Members'):
                    # do not duplicate Members sub-hierarchy as sections
                    # (does not really make sense, or does it?)
                    self.buildFolder(object, sc_el, 'Section')

        return root

    def createFolder(self, folder_id, portal_type, parent, props, dm):
        """Create a folder from scratch (not actually present
        in the portal's hierarchy)"""
        
        el = SubElement(parent, "{%s}folder" % self.ns_uri)
        # folder properties
        el.set('id', folder_id)
        el.set('portal_type', portal_type)
        el2 = SubElement(el, "{%s}datamodel" % self.ns_uri)
        for field_id, field_val in dm.items():
            el3 = SubElement(el2, "{%s}field" % self.ns_uri)
            el3.text = str(field_val)
            el3.set('name', field_id)
            el3.set('type', type(field_val).__name__)
        el2 = SubElement(el, "{%s}properties" % self.ns_uri)
        for property_id, property_val in props.items():
            el3 = SubElement(el2, "{%s}%s" % (self.ns_uri, property_id))
            el3.text = str(property_val)
            el3.set('type', type(property_val).__name__)
        return el
    
    def buildFolder(self, folder, parent, portal_type):
        """Build an elementtree representation of a folder"""

        if self.export_hierarchy_method in ('wssc', 'ws'):
            el = SubElement(parent, "{%s}folder" % self.ns_uri)
            # folder properties
            el.set('id', folder.id)
            el.set('portal_type', portal_type)
            # required by schema, even if empty
            el2a = SubElement(el, "{%s}datamodel" % self.ns_uri)
            el2b = SubElement(el, "{%s}properties" % self.ns_uri)
            for property_id, property_val in folder.propertyItems():
                if property_val:
                    el3 = SubElement(el2b, "{%s}%s" % (self.ns_uri, property_id))
                    el3.text = str(property_val)
                    el3.set('type', type(property_val).__name__)
                    if property_id == 'title':
                        # 'Title' seems to be the only property that
                        # can be retrieved and mapped to a CPS datamodel field
                        el3 = SubElement(el2a, "{%s}field" % self.ns_uri)
                        el3.text = str(property_val)
                        el3.set('name', 'Title')
                        el3.set('type', 'str')

        # process its children
        for object in folder.objectValues():
            if object.meta_type in ('Plone Folder', 'Large Plone Folder',
                                    'Folder'):
                self.buildFolder(object, el, portal_type)
