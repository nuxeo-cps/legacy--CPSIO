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

import os
import re
import locale

from zLOG import LOG, DEBUG, INFO, ERROR, WARNING
from elementtree.ElementTree import ElementTree
from elementtree.ElementPath import findall as xpath_findall
from elementtree.ElementPath import find as xpath_find

import Acquisition
from Acquisition import aq_base, aq_inner
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass, PersistentMapping
from DateTime.DateTime import DateTime
from OFS.Image import File, Image
from OFS.DTMLMethod import DTMLMethod
from Products.PageTemplates.ZopePageTemplate import ZopePageTemplate
from Products.PythonScripts.PythonScript import PythonScript

from Products.CMFCore.utils import UniqueObject
from Products.CMFCore.permissions import ManagePortal
from Products.CMFCore.utils import UniqueObject, getToolByName
from Products.CPSSchemas.Schema import SchemaContainer
from Products.CPSSchemas.Layout import LayoutContainer
from Products.CPSCore.EventServiceTool import getEventService

from Products.CPSIO.BaseImporter import MAIN_NAMESPACE_URI, BaseImporter
from Products.CPSIO.IOBase import IOBase

SUBTRANSACTION_COMMIT = 10

main_namespace_uri = 'http://www.nuxeo.com/2004/06/'
# adding 2 for surrounding curly braces {} of James Clark's NS syntax
# http://www.jclark.com/xml/xmlns.htm
main_namespace_uri_len = len(main_namespace_uri) + 2

def toLatin9(s):
    if s is None:
        return None
    else:
        try:
            s = unicode(s, locale.getpreferredencoding())
        except TypeError, e:
            # decoding Unicode is not supported
            s = unicode(s)
        return s.encode('iso-8859-15', 'ignore')

def proxySorter(x, y):
    if x[0] > y[0]:
        return 1
    elif y[0] > x[0]:
        return -1
    else:
        return 0

def booleanParser(literalValue, defaultValue=0):
    lit = literalValue.lower()
    if lit == 'true':
        return 1
    elif lit == 'false':
        return 0
    else:
        try:
            res = int(literalValue)
            return res
        except ValueError:
            return defaultValue

class Importer(BaseImporter):

    options_template = 'cps3importer_form'
    options_table = [
        {'id': 'import_hierarchy',
         'depth': 0,
         'title': "Import Hierarchy",
         'label': 'cpsio_label_import_hierarchy',
         },
        {'id': 'import_hierarchy_restore_local_roles',
         'depth': 1,
         'title': "Restore local roles",
         'label': 'cpsio_label_restore_local_roles',
         },
        {'id': 'import_hierarchy_restore_boxes',
         'depth': 1,
         'title': "Restore box configuration",
         'label': 'cpsio_label_restore_boxes',
         },
        {'id': 'import_hierarchy_restore_portlets',
         'depth': 1,
         'title': "Restore portlets",
         'label': 'cpsio_label_restore_portlets',
         },
        {'id': 'import_hierarchy_restore_local_themes',
         'depth': 1,
         'title': "Restore local themes",
         'label': 'cpsio_label_restore_local_themes',
         },
        {'id': 'import_documents',
         'depth': 0,
         'title': "Import documents",
         'label': 'cpsio_label_import_documents',
         },
        {'id': 'import_documents_overwrite',
         'depth': 1,
         'title': "Overwrite existing documents in case of conflict",
         'label': 'cpsio_label_overwrite_documents',
         },
        {'id': 'import_workflows',
         'depth': 0,
         'title': "Import workflows",
         'label': 'cpsio_label_import_workflows',
         },
        {'id': 'import_portal_types',
         'depth': 0,
         'title': "Import portal types",
         'label': 'cpsio_label_import_portal_types',
         },
        {'id': 'import_schemas',
         'depth': 0,
         'title': "Import schemas",
         'label': 'cpsio_label_import_schemas',
         },
        {'id': 'import_layouts',
         'depth': 0,
         'title': "Import layouts",
         'label': 'cpsio_label_import_layouts',
         },
        {'id': 'import_vocabularies',
         'depth': 0,
         'title': "Import vocabularies",
         'label': 'cpsio_label_import_vocabularies',
         },
        {'id': 'import_theme_settings',
         'depth': 0,
         'title': "Import theme settings",
         'label': 'cpsio_label_import_theme_settings',
         },
        {'id': 'import_custom_skins',
         'depth': 0,
         'title': "Import custom skins",
         'label': 'cpsio_label_import_custom_skins',
         },
        {'id': 'import_custom_skins_overwrite',
         'depth': 1,
         'title': "Overwrite existing items in case of conflict",
         'label': 'cpsio_label_overwrite_custom_skins',
         },
        {'id': 'import_members',
         'depth': 0,
         'title': "Import members",
         'label': 'cpsio_label_import_members',
         },
        {'id': 'import_groups',
         'depth': 0,
         'title': "Import groups",
         'label': 'cpsio_label_import_groups',
         },
        ]

    security = ClassSecurityInfo()
    security.declareObjectPublic()

    __roles__=None
    __allow_access_to_unprotected_subobjects__=1

    def __init__(self, portal):
        self.portal = portal
        self.ns_uri = main_namespace_uri + 'cps3#'

    security.declareProtected(ManagePortal, 'importFile')
    def importFile(self):
        """Main import"""

        self.log("Importing file " + self.file_path)
        LOG("Importing file", INFO, self.file_path)
        doc = ElementTree(file=self.file_path)
        root = doc.getroot()

        portal_type_file = self.getRef('cpsportaltypes', root)
        schema_file = self.getRef('cpsschemas', root)
        layout_file = self.getRef('cpslayouts', root)
        vocab_file = self.getRef('cpsvocabularies', root)
        skin_file = self.getRef('cmfcustomskins', root)
        workflow_file = self.getRef('cpsworkflows', root)
        hierarchy_file = self.getRef('cpshierarchy', root)
        doc_file = self.getRef('cpsdocuments', root)
        themesettings_file = self.getRef('themesettings', root)
        members_file = self.getRef('cpsmembers', root)
        groups_file = self.getRef('cpsgroups', root)
        subscriptions_file = self.getRef('cpssubscriptions', root)

        if 'import_members' in self.options:
            GroupsImporter(self.portal, groups_file, self.dir_name).importFile()
            MembersImporter(self.portal, members_file, self.dir_name).importFile()
        elif 'import_groups' in self.options:
            GroupsImporter(self.portal, groups_file, self.dir_name).importFile()
        if 'import_portal_types' in self.options and portal_type_file:
            PortalTypeImporter(self.portal, portal_type_file, self.dir_name).importFile()
        if 'import_schemas' in self.options and schema_file:
            SchemaImporter(self.portal, schema_file, self.dir_name).importFile()
        if 'import_layouts' in self.options and layout_file:
            LayoutImporter(self.portal, layout_file, self.dir_name).importFile()
        if 'import_vocabularies' in self.options and vocab_file:
            VocabImporter(self.portal, vocab_file, self.dir_name).importFile()
        if 'import_custom_skins' in self.options and skin_file:
            icso = 'import_custom_skins_overwrite' in self.options
            SkinImporter(self.portal, skin_file, self.dir_name, icso).importFile()
        if 'import_workflows' in self.options and workflow_file:
            WorkflowImporter(self.portal, workflow_file, self.dir_name).importFile()
        if (('import_hierarchy' in self.options or 'import_documents' in self.options)
            and hierarchy_file):
            rlr = 'import_hierarchy_restore_local_roles' in self.options
            rbx = 'import_hierarchy_restore_boxes' in self.options
            rpl = 'import_hierarchy_restore_portlets' in self.options
            rlt = 'import_hierarchy_restore_local_themes' in self.options
            HierarchyImporter(self.portal, hierarchy_file, self.dir_name, rlr, rbx, rpl, rlt).importFile()
            # import subscriptions
            #SubscriptionsImporter(self.portal, subscriptions_file, self.dir_name).importFile()
        if 'import_documents' in self.options and doc_file:
            ido = 'import_documents_overwrite' in self.options
            DocumentImporter(self.portal, doc_file, self.dir_name, ido).importFile()
        if 'import_theme_settings' in self.options and themesettings_file:
            ThemeSettingsImporter(self.portal, themesettings_file, self.dir_name).importFile()

    def getRef(self, elem_name, el):
        els = xpath_findall(el, "{%s}%s" % (self.ns_uri, elem_name))
        if len(els) > 0:
            return els[0].get('ref')
        else:
            return None

InitializeClass(Importer)

#
# CPS 3 Portal Type Importer
#
class PortalTypeImporter(IOBase):

    def __init__(self, portal, file_name, dir_name):
        self.portal = portal
        self.pt_tool = self.portal.portal_types
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name, self.file_name)
        self.ns_uri = main_namespace_uri + 'cpsportaltypes#'
        self.elementtree_ns_uri = "{%s}" % self.ns_uri
        # adding 2 for surrounding curly braces {} of James Clark's NS syntax
        self.ns_uri_len = len(self.ns_uri) + 2

    def importFile(self):
        """Parse the XML file into an elementtree structure"""

        self.log("Importing portal types from file " + self.file_path)
        LOG("Importing portal types from file", INFO, self.file_path)

        doc = ElementTree(file=self.file_path)
        self.updateTypes(doc.getroot())

    def updateTypes(self, root):
        """Process the elementtree and call appropriate builders"""

        #get all CMF Factory-based Type Information definitions
        cmffti_els = xpath_findall(root, "{%s}cmffti" % self.ns_uri)
        factory_based_type_infos = {}
        for el in cmffti_els:
            fbti = self.buildCMFType(el)
            if fbti:
                pid = fbti.get('id')
                del fbti['id']
                factory_based_type_infos[pid] = fbti
        self.verifyFactoryBasedTypes(factory_based_type_infos)

        #get all CPS Flexible Type Information definitions
        cpsfti_els = xpath_findall(root, "{%s}cpsfti" % self.ns_uri)
        cps_flex_type_infos = {}
        for el in cpsfti_els:
            cps_flex_type_info = self.buildCPSType(el)
            if cps_flex_type_info:
                pid = cps_flex_type_info.get('id')
                del cps_flex_type_info['id']
                cps_flex_type_infos[pid] = cps_flex_type_info
        self.verifyFlexibleTypes(cps_flex_type_infos)

    def buildCMFType(self, el):
        """Build a Factory-based Type Information instance

        (from XML http://www.nuxeo.com/2004/06/cpsportaltypes#cmffti element)"""
        type_def = {}
        type_def['id'] = el.get('id')
        for xml_attr_name, xml_attr_val in el.items():
            if xml_attr_name in ('allow_discussion', 'cps_is_searchable',
                                 'cps_display_as_document_in_listing',
                                 'global_allow', 'filter_content_types',
                                 'cps_is_searchable', 'cps_is_portalbox'):
                try:
                    type_def[xml_attr_name] = booleanParser(xml_attr_val)
                except:
                    self.log("CPS3Importer: Failed to parse property %s of type %s" %
                             (xml_attr_name, type_def['id']))
                    LOG("CPS3Importer.PortalTypeImporter", ERROR,
                        "Failed to parse property %s of type %s" %
                        (xml_attr_name, type_def['id']))
            else:
                type_def[xml_attr_name] = xml_attr_val
        for xml_elem in el.getchildren():
            # only process elements in the cps portal type namespace
            if xml_elem.tag.startswith(self.elementtree_ns_uri):
                xml_elem_name = xml_elem.tag[self.ns_uri_len:]
                if xml_elem_name == 'actions':
                    # actions are processed later
                    actions_elem = xml_elem
                    continue
                dt = xml_elem.get('type')
                xml_elem_val = xml_elem.text
                if xml_elem_val:
                    try:
                        if dt == 'tuple':
                            xml_elem_val = eval("('" + xml_elem_val.replace(",","','") + "',)", {})
                        elif dt == 'list':
                            xml_elem_val = eval("['" + xml_elem_val.replace(",","','") + "',]", {})
                        elif dt == 'int':
                            xml_elem_val = int(xml_elem_val)
                        type_def[xml_elem_name] = xml_elem_val
                    except (SyntaxError, ValueError), err:
                        self.log("CPS3Importer: Failed to parse property %s of type %s: %s" %
                            (xml_elem_name, type_def['id'], err))
                        LOG("CPS3Importer.PortalTypeImporter", ERROR,
                            "Failed to parse property %s of type %s: %s" %
                            (xml_elem_name, type_def['id'], err))

        # process actions
        if actions_elem:
            actions = self.getActions(actions_elem)
            if len(actions):
                type_def['actions'] = actions

        return type_def

    def buildCPSType(self, el):
        """Build a CPS Flexible Type Information instance

        (from XML http://www.nuxeo.com/2004/06/cpsportaltypes#cpsfti element)"""
        type_def = {}
        type_def['id'] = el.get('id')
        for xml_attr_name, xml_attr_val in el.items():
            if xml_attr_name in ('allow_discussion', 'cps_is_searchable',
                                 'cps_display_as_document_in_listing',
                                 'global_allow', 'filter_content_types',
                                 'cps_is_searchable'):
                try:
                    type_def[xml_attr_name] = booleanParser(xml_attr_val)
                except:
                    self.log("CPS3Importer: Failed to parse property %s of type %s" %
                             (xml_attr_name, type_def['id']))
                    LOG("CPS3Importer.PortalTypeImporter", ERROR,
                        "Failed to parse property %s of type %s" %
                        (xml_attr_name, type_def['id']))
            else:
                type_def[xml_attr_name] = xml_attr_val
        actions_elem = None
        for xml_elem in el.getchildren():
            # only process elements in the cps portal type namespace
            if xml_elem.tag.startswith(self.elementtree_ns_uri):
                xml_elem_name = xml_elem.tag[self.ns_uri_len:]
                if xml_elem_name == 'actions':
                    # actions are processed later
                    actions_elem = xml_elem
                    continue
                dt = xml_elem.get('type')
                xml_elem_val = xml_elem.text
                if xml_elem_val:
                    try:
                        if dt == 'tuple':
                            xml_elem_val = eval("('" + xml_elem_val.replace(",","','") + "',)", {})
                        elif dt == 'list':
                            xml_elem_val = eval("['" + xml_elem_val.replace(",","','") + "',]", {})
                        elif dt == 'int':
                            xml_elem_val = int(xml_elem_val)
                        type_def[xml_elem_name] = xml_elem_val
                    except (SyntaxError, ValueError), err:
                        self.log("CPS3Importer: Failed to parse property %s of type %s: %s" %
                                 (xml_elem_name, type_def['id'], err))
                        LOG("CPS3Importer.PortalTypeImporter", ERROR,
                            "Failed to parse property %s of type %s: %s" %
                            (xml_elem_name, type_def['id'], err))
        # process actions
        if actions_elem:
            actions = self.getActions(actions_elem)
            if len(actions):
                type_def['actions'] = actions

        return type_def

    def getActions(self, actions_elem):
        actions = ()
        for xml_elem in xpath_findall(actions_elem, "%saction" % self.elementtree_ns_uri):
            action = {}
            for xml_attr_name, xml_attr_val in xml_elem.items():
                if xml_attr_name in ('visibility',):
                    try:
                        action['visible'] = booleanParser(xml_attr_val)
                    except:
                        self.log("CPS3Importer: Failed to parse action property %s for type %s" %
                                 (xml_attr_name, type_def['id']))
                        LOG("CPS3Importer.PortalTypeImporter", ERROR,
                            "Failed to parse action property %s for type %s" %
                            (xml_attr_name, type_def['id']))
                else:
                    # covers 'id', 'name', 'category'
                    action[xml_attr_name] = xml_attr_val
            for xml_elem2 in xml_elem.getchildren():
                if xml_elem2.tag.startswith(self.elementtree_ns_uri):
                    # only process elements in the cps portal type namespace
                    xml_elem2_name = xml_elem2.tag[self.ns_uri_len:]
                    xml_elem2_val = xml_elem2.text
                    if xml_elem2_name == 'expression':
                        action['action'] = xml_elem2_val
                    elif xml_elem2_name == 'permission':
                        action['permissions'] = (xml_elem2_val,)
                    else:
                        # covers 'condition'
                        action['condition'] = xml_elem2_val
            actions = actions + (action,)
        return actions

    def verifyFlexibleTypes(self, type_data):
        ttool = self.portal.portal_types
        ptypes_installed = ttool.objectIds()
        display_in_cmf_calendar = []
        for ptype, data in type_data.items():
            self.log("CPS3Importer: Adding type '%s'" % ptype)
            LOG('CPS3Importer:', DEBUG, "Adding type '%s'" % ptype)
            if ptype in ptypes_installed:
                ob = ttool[ptype]
                if ob.meta_type != 'Factory-based Type Information' and \
                   hasattr(ob, 'isUserModified') and \
                   ob.isUserModified():
                    self.log("CPS3Importer: 'WARNING: The type is modified and will not be changed. Delete manually if needed.")
                    LOG('CPS3Importer:', DEBUG, 'WARNING: The type is modified and will not be changed. Delete manually if needed.')
                    continue
                else:
                    self.log("CPS3Importer:    Deleting old definition")
                    LOG('CPS3Importer:', DEBUG, '   Deleting old definition')
                    ttool.manage_delObjects([ptype])

            ti = ttool.addFlexibleTypeInformation(id=ptype)
            if data.get('display_in_cmf_calendar'):
                display_in_cmf_calendar.append(ptype)
                del data['display_in_cmf_calendar']
            ti.manage_changeProperties(**data)
            self.log("CPS3Importer:  Added")
            LOG('CPS3Importer:', DEBUG, "  Added")

            if data.has_key('actions'):
                self.log("CPS3Importer:     Setting actions")
                LOG('CPS3Importer:', DEBUG, "    Setting actions")
                nb_action = len(ti.listActions())
                ti.deleteActions(selections=range(nb_action))
                for a in data['actions']:
                    self.addAction(ti, a)

    def verifyFactoryBasedTypes(self, type_data):
        ttool = self.portal.portal_types
        ptypes_installed = ttool.objectIds()
        display_in_cmf_calendar = []
        for ptype, data in type_data.items():
            self.log("CPS3Importer: Adding type '%s'" % ptype)
            LOG('CPS3Importer:', DEBUG, "Adding type '%s'" % ptype)
            if ptype in ptypes_installed:
                ob = ttool[ptype]
                if ob.meta_type != 'Factory-based Type Information' and \
                   hasattr(ob, 'isUserModified') and \
                   ob.isUserModified():
                    self.log("CPS3Importer: WARNING: The type is modified and will not be changed. Delete manually if needed.")
                    LOG('CPS3Importer:', DEBUG, 'WARNING: The type is modified and will not be changed. Delete manually if needed.')
                    continue
                else:
                    self.log("CPS3Importer:    Deleting old definition")
                    LOG('CPS3Importer:', DEBUG, '   Deleting old definition')
                    ttool.manage_delObjects([ptype])
            tin = None
            if data.get('product', None) and data.get('content_meta_type', None):
                tin = '%s: %s (%s)' % (data['product'], data['content_meta_type'],
                                       data['content_meta_type'])
            try:
                # this is to prevent errors thrown when a product is not installed
                # (e.g. CMFPlone)
                ttool.manage_addTypeInformation(id=ptype,
                                                add_meta_type='Factory-based Type Information',
                                                typeinfo_name=tin)
                ti = ttool[ptype]
                if data.get('display_in_cmf_calendar'):
                    display_in_cmf_calendar.append(ptype)
                    del data['display_in_cmf_calendar']
                ti.manage_changeProperties(**data)
                self.log("CPS3Importer:   Added")
                LOG('CPS3Importer:', DEBUG, "  Added")
                if data.has_key('actions'):
                    self.log("CPS3Importer:    Setting actions")
                    LOG('CPS3Importer:', DEBUG, "    Setting actions")
                    nb_action = len(ti.listActions())
                    ti.deleteActions(selections=range(nb_action))
                    for a in data['actions']:
                        self.addAction(ti, a)
            except:
                self.log("CPS3Importer: Factory-based Type information %s could not be imported" % tin)
                LOG('CPS3Importer',ERROR,'Factory-based Type information %s could not be imported' % tin)

    def addAction(self, object, properties):
        """Adds an action to an object

        Fixes up some properties first.
        """

        # ActionInformation.__init__() uses 'permissions' as a
        # parameter, but addAction() uses 'permission'. We will
        # allow both.
        if properties.has_key('permissions'):
            properties['permission'] = properties['permissions']
            del properties['permissions']
        if not properties.has_key('permission'):
            properties['permission'] = ''
        # For backward compatibility, visible should default to 1:
        if not properties.has_key('visible'):
            properties['visible'] = 1
        # And category to 'object':
        if not properties.has_key('category'):
            properties['category'] = 'object'
        # Condition must be present, even empty
        if not properties.has_key('condition'):
            properties['condition'] = ''
        object.addAction(**properties)

#
# CPS 3 Schema Importer
#
class SchemaImporter(IOBase):

    def __init__(self, portal, file_name, dir_name):
        self.portal = portal
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name, self.file_name)
        self.ns_uri = main_namespace_uri + 'cpsschemas#'
        self.elementtree_ns_uri = "{%s}" % self.ns_uri
        # adding 2 for surrounding curly braces {} of James Clark's NS syntax
        self.ns_uri_len = len(self.ns_uri) + 2

    def importFile(self):
        """Parse the XML file into an elementtree structure"""

        self.log("Importing schemas from file " + self.file_path)
        LOG("Importing schemas from file", INFO, self.file_path)

        doc = ElementTree(file=self.file_path)
        self.updateSchemas(doc.getroot())

    def updateSchemas(self, root):
        """Process the elementtree"""

        #get all schema definitions
        schema_els = xpath_findall(root, "{%s}schema" % self.ns_uri)
        schemas = {}
        for el in schema_els:
            schema_def = self.buildSchema(el)
            if schema_def:
                id = schema_def.get('_id')
                del schema_def['_id']
                schemas[id] = schema_def
        self.verifySchemas(schemas, schema_container=self.portal.portal_schemas)

    def buildSchema(self, el):
        """Build a schema definition

        (from XML http://www.nuxeo.com/2004/06/cpsschemas#schema element)"""

        schema_def = {}
        schema_def['_id'] = el.get('id')
        for field_el in xpath_findall(el, "{%s}field" % self.ns_uri):
            field_def = self.buildField(field_el)
            if field_def:
                id = field_def.get('_id')
                del field_def['_id']
                schema_def[id] = field_def
        return schema_def

    def buildField(self, el):
        field_def = {}
        field_def['type'] = el.get('field_type')
        field_def['data'] = {}
        field_def['_id'] = el.get('id')
        # XPath support in elementtree is extremely limited
        # we cannot express NS-based xpath expressions and have
        # to filter manually
        for prop_el in [el2 for el2 in
                        xpath_findall(el, "*")
                        if el2.tag.startswith(self.elementtree_ns_uri)]:
            prop_name = prop_el.tag[self.ns_uri_len:]
            prop_value_text = prop_el.text
            prop_value_type = prop_el.get('type')
            if (prop_value_type == 'int' or prop_value_type == 'list' or\
                prop_value_type == 'tuple'):
                try:
                    prop_value = eval(prop_value_text)
                except (SyntaxError, ValueError), err:
                    prop_value = prop_value_text
                    self.log("CPS3Importer: Failed to parse property %s of schema field %s: %s" %
                             (prop_name, field_def['_id'], err))
                    LOG("CPS3Importer.SchemaImporter", ERROR,
                        "Failed to parse property %s of schema field %s: %s" %
                        (prop_name, field_def['_id'], err))
            else:
                prop_value = toLatin9(prop_value_text)
            field_def['data'][prop_name] = prop_value

        return field_def

    #
    # CPSSchemas installation
    #
    def verifySchemas(self, schemas, schema_container=None):
        """Add schemas"""
        stool = schema_container or self.portal.portal_schemas
        existing_schemas = stool.objectIds()
        for id, info in schemas.items():
            self.log("CPS3Importer: Checking schema %s" % id)
            LOG('CPS3Importer:', DEBUG, 'Checking schema %s' % id)
            if id in existing_schemas:
                schema = stool['id']
                if (hasattr(schema, 'isUserModified') and
                    schema.isUserModified()):
                    self.log("CPS3Importer:  WARNING: Schema has been modified and will not be changed. Delete manually if necessary.")
                    LOG('CPS3Importer:', DEBUG, '  WARNING: Schema has been modified and will not be changed. Delete manually if necessary.')
                    continue
                else:
                    self.log("CPS3Importer:   Deleting old definition")
                    LOG('CPS3Importer:', DEBUG, '  Deleting old definition')
                    stool.manage_delObjects(id)
            schema = stool.manage_addCPSSchema(id)
            for field_id, fieldinfo in info.items():
                schema.manage_addField(field_id, fieldinfo['type'],
                                       **fieldinfo['data'])

#
# CPS 3 Layout Importer
#
class LayoutImporter(IOBase):

    def __init__(self, portal, file_name, dir_name):
        self.portal = portal
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name, self.file_name)
        self.ns_uri = main_namespace_uri + 'cpslayouts#'
        self.elementtree_ns_uri = "{%s}" % self.ns_uri
        # adding 2 for surrounding curly braces {} of James Clark's NS syntax
        self.ns_uri_len = len(self.ns_uri) + 2

    def importFile(self):
        """Parse the XML file into an elementtree structure"""

        self.log("Importing layouts from file " + self.file_path)
        LOG("Importing layouts from file", INFO, self.file_path)

        doc = ElementTree(file=self.file_path)
        self.updateLayouts(doc.getroot())

    def updateLayouts(self, root):
        """Process the elementtree"""

        # then get all layout definitions
        layout_els = xpath_findall(root, "{%s}layout" % self.ns_uri)
        layouts = {}
        for el in layout_els:
            layout_def = self.buildLayout(el)
            if layout_def:
                id = layout_def.get('_id')
                del layout_def['_id']
                layouts[id] = layout_def
        self.verifyLayouts(layouts, layout_container=self.portal.portal_layouts)

    def buildLayout(self, el):
        """Build a layout definition

        (from XML http://www.nuxeo.com/2004/06/cpslayouts#layout element)"""

        from types import ListType
        # misc properties
        layout_def = {'widgets':{},
                      'layout':{}}
        layout_def['_id'] = el.get('id')
        layout_def['layout']['ncols'] = el.get('ncols')
        layout_def['layout']['style_prefix'] = el.get('style_prefix')
        # flexible widgets
        flexible_widgets = ()
        fw_els = xpath_findall(el, "{%s}flexible_widgets" % self.ns_uri)
        if len(fw_els) and fw_els[0].text:
            flexible_widgets = eval(fw_els[0].text)
            if isinstance(flexible_widgets, ListType):
                flexible_widgets = tuple(flexible_widgets)
        layout_def['layout']['flexible_widgets'] = flexible_widgets
        # widgets
        widget_els = xpath_findall(xpath_findall(el, "{%s}widgets" % self.ns_uri)[0],
                                "{%s}widget" % self.ns_uri)
        widgets = {}
        for widget_el in widget_els:
            widget = self.buildWidget(widget_el)
            if widget:
                id = widget.get('_id')
                del widget['_id']
                widgets[id] = widget
        layout_def['widgets'] = widgets
        # rows
        row_els = xpath_findall(xpath_findall(el, "{%s}rows" % self.ns_uri)[0],
                                "{%s}row" % self.ns_uri)
        rows = []
        for row_el in row_els:
            row = self.buildRow(row_el)
            if row:
                rows.append(row)
        layout_def['layout']['rows'] = rows
        return layout_def

    def buildWidget(self, el):
        """Build a widget definition

        (from XML http://www.nuxeo.com/2004/06/cpslayouts#widget element)"""

        widget = {}
        widget['_id'] = el.get('id')

        data = {}
        for attr in ('title', 'label', 'label_edit'):
            data[attr] = el.get(attr, '')
        for attr in ('is_required', 'is_i18n', 'hidden_empty'):
            data[attr] = booleanParser(el.get(attr))
        # XPath support in elementtree is extremely limited
        # we cannot express NS-based xpath expressions and have
        # to filter manually
        for prop_el in [el2 for el2 in
                        xpath_findall(el, "*")
                        if el2.tag.startswith(self.elementtree_ns_uri)]:
            prop_name = prop_el.tag[self.ns_uri_len:]
            prop_value_text = prop_el.text
            prop_value_type = prop_el.get('type')
            if prop_value_text:
                if (prop_value_type == 'int' or prop_value_type == 'list' or\
                    prop_value_type == 'tuple'):
                    try:
                        prop_value = eval(prop_value_text)
                    except (SyntaxError, ValueError), err:
                        prop_value = prop_value_text
                        self.log("CPS3Importer: Failed to parse property %s of layout widget %s: %s" %
                                 (prop_name, widget['_id'], err))
                        LOG("CPS3Importer.LayoutImporter", ERROR,
                            "Failed to parse property %s of layout widget %s: %s" %
                            (prop_name, widget['_id'], err))
                else:
                    prop_value = prop_value_text
            else:
                prop_value = ''
            data[prop_name] = prop_value

        widget['data'] = data
        widget['type'] = el.get('widget_type')
        return widget

    def buildRow(self, el):
        """Build a layout row definition

        (from XML http://www.nuxeo.com/2004/06/cpslayouts#row element)"""

        row = []
        cell_els = xpath_findall(el, "{%s}cell" % self.ns_uri)
        for cell_el in cell_els:
            cell = {}
            cell['widget_id'] = cell_el.get('widget_id')
            ncols = cell_el.get('ncols', None)
            if ncols:
               cell['ncols'] = int(ncols)
            row.append(cell)
        return row

    #
    # Layout installation
    #
    def verifyLayouts(self, layouts, layout_container=None):
        """Add layouts"""

        ltool = layout_container or self.portal.portal_layouts
        existing_layouts = ltool.objectIds()
        for id, info in layouts.items():
            self.log("CPS3Importer: Checking layout %s" % id)
            LOG('CPS3Importer:', DEBUG, 'Checking layout %s' % id)
            if id in existing_layouts:
                ob = ltool[id]
                if hasattr(ob, 'isUserModified') and \
                   ob.isUserModified():
                    self.log("CPS3Importer:   WARNING: Layout has been modified and will not be changed. Delete manually if necessary.")
                    LOG('CPS3Importer:', DEBUG, '  WARNING: Layout has been modified and will not be changed. Delete manually if necessary.')
                    continue
                else:
                    self.log("CPS3Importer:  Deleting old definition")
                    LOG('CPS3Importer:', DEBUG, '  Deleting old definition')
                    ltool.manage_delObjects([id])
            layout = ltool.manage_addCPSLayout(id)

            for widget_id, widgetinfo in info['widgets'].items():
                layout.manage_addCPSWidget(widget_id, widgetinfo['type'],
                                           **widgetinfo['data'])
            layout.setLayoutDefinition(info['layout'])
            layout.manage_changeProperties(**info['layout'])

#
# CPS 3 Skin Importer
#
class SkinImporter(IOBase):

    def __init__(self, portal, file_name, dir_name, icso):
        self.portal = portal
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name, self.file_name)
        self.ns_uri = main_namespace_uri + 'cmfskins#'
        self.elementtree_ns_uri = "{%s}" % self.ns_uri
        # adding 2 for surrounding curly braces {} of James Clark's NS syntax
        self.ns_uri_len = len(self.ns_uri) + 2
        self.skin_dir = self.portal.portal_skins.custom
        self.item_overwrite = icso

    def importFile(self):
        """Parse the XML file into an elementtree structure"""

        self.log("Importing custom skins from file " + self.file_path)
        LOG("Importing custom skins from file", INFO, self.file_path)

        doc = ElementTree(file=self.file_path)
        self.updateCustomSkins(doc.getroot())

    def updateCustomSkins(self, root_el):
        file_els = xpath_findall(root_el, "{%s}file" % self.ns_uri)
        for file_el in file_els:
            self.buildFile(file_el)
        pt_els = xpath_findall(root_el, "{%s}pageTemplate" % self.ns_uri)
        for pt_el in pt_els:
            self.buildPageTemplate(pt_el)
        dtml_els = xpath_findall(root_el, "{%s}dtmlMethod" % self.ns_uri)
        for dtml_el in dtml_els:
            self.buildDTMLMethod(dtml_el)

    def buildFile(self, file_el):
        id = file_el.get('id')
        content_type = file_el.get('content_type')
        title = file_el.get('title')
        data_file_rpath = file_el.get('ref')
        data_file_path = os.path.join(CLIENT_HOME, self.dir_name, data_file_rpath)
        data_file = open(data_file_path, 'rb')
        f = File(id, title, data_file, content_type=content_type)
        if id in self.skin_dir.objectIds():
            if self.item_overwrite:
                self.skin_dir.manage_delObjects([id])
                self.skin_dir._setObject(id, f)
        else:
            self.skin_dir._setObject(id, f)

    def buildPageTemplate(self, pt_el):
        id = pt_el.get('id')
        content_type = pt_el.get('content_type')
        title = pt_el.get('title')
        data_file_rpath = pt_el.get('ref')
        data_file_path = os.path.join(CLIENT_HOME, self.dir_name, data_file_rpath)
        data_file = open(data_file_path, 'r')
        text = '\n'.join(data_file.readlines())
        zpt = ZopePageTemplate(id, text=text, content_type=content_type)
        zpt.pt_setTitle(title)
        if id in self.skin_dir.objectIds():
            if self.item_overwrite:
                self.skin_dir.manage_delObjects([id])
                self.skin_dir._setObject(id, zpt)
        else:
            self.skin_dir._setObject(id, zpt)

    def buildDTMLMethod(self, dtml_el):
        id = dtml_el.get('id')
        title = dtml_el.get('title')
        data_file_rpath = dtml_el.get('ref')
        data_file_path = os.path.join(CLIENT_HOME, self.dir_name, data_file_rpath)
        data_file = open(data_file_path, 'r')
        dtml = DTMLMethod('\n'.join(data_file.readlines()), __name__=id)
        dtml.title = title
        if id in self.skin_dir.objectIds():
            if self.item_overwrite:
                self.skin_dir.manage_delObjects([id])
                self.skin_dir._setObject(id, dtml)
        else:
            self.skin_dir._setObject(id, dtml)

#
# CPS 3 Vocabulary Importer
#
class VocabImporter(IOBase):

    def __init__(self, portal, file_name, dir_name):
        self.portal = portal
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name, self.file_name)
        self.ns_uri = main_namespace_uri + 'cpsvocabularies#'
        self.elementtree_ns_uri = "{%s}" % self.ns_uri
        # adding 2 for surrounding curly braces {} of James Clark's NS syntax
        self.ns_uri_len = len(self.ns_uri) + 2

    def importFile(self):
        """Parse the XML file into an elementtree structure"""

        self.log("Importing vocabularies from file " + self.file_path)
        LOG("Importing vocabularies from file", INFO, self.file_path)

        doc = ElementTree(file=self.file_path)
        self.updateVocabularies(doc.getroot())

    def updateVocabularies(self, root):
        """Process the elementtree"""

        # get all vocabulary definitions
        vocab_els = xpath_findall(root, "{%s}cpsVocabulary" % self.ns_uri)
        vocabs = {}
        for el in vocab_els:
            vocab = self.buildCPSVocabulary(el)
            if vocab:
                id = vocab.get('_id')
                del vocab['_id']
                vocabs[id] = vocab
        self.verifyVocabularies(vocabs)
        vocab_els = xpath_findall(root, "{%s}methodVocabulary" % self.ns_uri)
        vocabs = {}
        for el in vocab_els:
            vocab = self.buildMethodVocabulary(el)
            if vocab:
                id = vocab.get('_id')
                del vocab['_id']
                vocabs[id] = vocab
        self.verifyVocabularies(vocabs)
        vocab_els = xpath_findall(root, "{%s}directoryVocabulary" % self.ns_uri)
        vocabs = {}
        for el in vocab_els:
            vocab = self.buildDirectoryVocabulary(el)
            if vocab:
                id = vocab.get('_id')
                del vocab['_id']
                vocabs[id] = vocab
        self.verifyVocabularies(vocabs)
        vocab_els = xpath_findall(root,
                                  "{%s}directoryEntryVocabulary" % self.ns_uri)
        vocabs = {}
        for el in vocab_els:
            vocab = self.buildDirectoryVocabulary(el, entry_vocab=1)
            if vocab:
                id = vocab.get('_id')
                del vocab['_id']
                vocabs[id] = vocab
        self.verifyVocabularies(vocabs)

    def buildCPSVocabulary(self, el):
        """Build a CPS Vocabulary

        (from XML http://www.nuxeo.com/2004/06/cpsvocabularies#cpsVocabulary element)"""

        vocab = {'type': 'CPS Vocabulary',
                 'data': {}}
        vocab['_id'] = el.get('id')
        # parse vocabulary properties
        title = el.get('title', None)
        title_msgid = el.get('title_msgid', None)
        acl_write_roles = el.get('acl_write_roles', None)
        if title:
            vocab['data']['title'] = toLatin9(title)
        #XXX: don't know why, but title_msgid/description/acl_write_roles
        # are not taken into account (don't know if it is possible, as
        # they are never specified in any of the available vocabularies)
        # weird thing is that it works for Method vocabs
        if title_msgid:
            vocab['data']['title_msgid'] = title_msgid
        if acl_write_roles:
            vocab['data']['acl_write_roles'] = acl_write_roles
        description = xpath_findall(el, "{%s}description" % self.ns_uri)
        if len(description) > 0 and description[0].text:
            vocab['data']['description'] = toLatin9(description[0].text)
        # parse vocabulary items
        items = []
        for item_el in xpath_findall(el, "{%s}item" % self.ns_uri):
            msgid = item_el.get('msgid', None)
            if msgid is not None:
                items.append((item_el.get('key'), item_el.text, msgid))
            else:
                items.append((item_el.get('key'), item_el.text))
        vocab['data']['tuples'] = items
        return vocab

    def buildMethodVocabulary(self, el):
        """Build a CPS Method Vocabulary

        (from XML http://www.nuxeo.com/2004/06/cpsvocabularies#methodVocabulary element)"""

        vocab = {'type': 'CPS Method Vocabulary',
                 'data': {}}
        vocab['_id'] = el.get('id')
        vocab['data']['get_vocabulary_method'] = el.get('get_vocabulary_method')
        # parse vocabulary properties
        title = el.get('title', None)
        title_msgid = el.get('title_msgid', None)
        add_empty_key = el.get('add_empty_key', None)
        empty_key_pos = el.get('empty_key_pos', None)
        if title:
            vocab['data']['title'] = toLatin9(title)
        if title_msgid:
            vocab['data']['title_msgid'] = title_msgid
        if add_empty_key:
            vocab['data']['add_empty_key'] = booleanParser(add_empty_key)
        if empty_key_pos:
            vocab['data']['empty_key_pos'] = empty_key_pos
        description = xpath_findall(el, "{%s}description" % self.ns_uri)
        if len(description) > 0 and description[0].text:
            vocab['data']['description'] = toLatin9(description[0].text)
        empty_key_value = xpath_findall(el,
                                        "{%s}empty_key_value" % self.ns_uri)
        if len(empty_key_value) > 0 and empty_key_value[0].text:
            vocab['data']['empty_key_value'] = toLatin9(empty_key_value[0].text)
        return vocab

    def buildDirectoryVocabulary(self, el, entry_vocab=0):
        """Build a CPS Directory Vocabulary

        (from XML http://www.nuxeo.com/2004/06/cpsvocabularies#directoryVocabulary element)
        (from XML http://www.nuxeo.com/2004/06/cpsvocabularies#directoryEntryVocabulary element)"""

        vocab = {'data': {}}
        if entry_vocab:
            vocab['type'] = 'CPS Directory Entry Vocabulary'
        else:
            vocab['type'] = 'CPS Directory Vocabulary'
        vocab['_id'] = el.get('id')
        vocab['data']['directory'] = el.get('directory')
        # parse vocabulary properties
        title = el.get('title', None)
        title_msgid = el.get('title_msgid', None)
        add_empty_key = el.get('add_empty_key', None)
        empty_key_pos = el.get('empty_key_pos', None)
        if title:
            vocab['data']['title'] = toLatin9(title)
        if title_msgid:
            vocab['data']['title_msgid'] = title_msgid
        if add_empty_key:
            vocab['data']['add_empty_key'] = booleanParser(add_empty_key)
        if empty_key_pos:
            vocab['data']['empty_key_pos'] = empty_key_pos
        description = xpath_findall(el, "{%s}description" % self.ns_uri)
        if len(description) > 0 and description[0].text:
            vocab['data']['description'] = toLatin9(description[0].text)
        empty_key_value = xpath_findall(el, "{%s}empty_key_value" % self.ns_uri)
        if len(empty_key_value) > 0 and empty_key_value[0].text:
            vocab['data']['empty_key_value'] = toLatin9(empty_key_value[0].text)
        return vocab

    def verifyVocabularies(self, vocabularies):
        """Adds vocabularies"""

        vtool = self.portal.portal_vocabularies
        existing_vocabularies = vtool.objectIds()
        for id, info in vocabularies.items():
            self.log("CPS3Importer: Checking vocabulary %s" % id)
            LOG('CPS3Importer:', DEBUG, 'Checking vocabulary %s' % id)
            if id in existing_vocabularies:
                p = vtool[id]
                if p.isUserModified():
                    self.log("CPS3Importer:   WARNING: Vocabulary has been modified and will not be changed. Delete manually if necessary.")
                    LOG('CPS3Importer:', DEBUG, '  WARNING: Vocabulary has been modified and will not be changed. Delete manually if necessary.')
                    continue
                else:
                    self.log("CPS3Importer:  Deleting old definition")
                    LOG('CPS3Importer:', DEBUG, '  Deleting old definition')
                    vtool.manage_delObjects([id])
            vtype = info.get('type', 'CPS Vocabulary')
            vtool.manage_addCPSVocabulary(id, vtype, **info['data'])


#
# CPS 3 Hierarchy Importer
#
class HierarchyImporter(IOBase):

    def __init__(self, portal, file_name, dir_name, restore_local_roles, restore_boxes, restore_portlets, restore_local_themes):
        self.portal = portal
        self.wtool = self.portal.portal_workflow
        self.evtool = getEventService(self.portal)
        self.mtool = self.portal.portal_membership
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name, self.file_name)
        self.ns_uri = main_namespace_uri + 'cpshierarchy#'
        self.elementtree_ns_uri = "{%s}" % self.ns_uri
        # adding 2 for surrounding curly braces {} of James Clark's NS syntax
        self.ns_uri_len = len(self.ns_uri) + 2
        self.restore_local_roles = restore_local_roles
        self.restore_boxes = restore_boxes
        self.restore_portlets = restore_portlets
        self.restore_local_themes = restore_local_themes

    def importFile(self):
        """Parse the XML file into an elementtree structure"""

        self.log("Importing hierarchy from file" + self.file_path)
        LOG("Importing hierarchy from file", INFO, self.file_path)

        doc = ElementTree(file=self.file_path)
        root = doc.getroot()
        # get all root folders, build them if they do not exist,
        # then build their children (recursive descent of the XML tree)
        folder_els = xpath_findall(root, "{%s}folder" % self.ns_uri)
        for folder_el in folder_els:
            self.buildFolder(folder_el, self.portal)
        # root boxes
        if self.restore_boxes:
            boxes_els = xpath_findall(root,
                                      "{%s}boxes" % self.ns_uri)
            if boxes_els:
                self.setupBoxes(self.portal, boxes_els[0], idbc='.cps_boxes_root')
        # root portlets
        if self.restore_portlets:
            self.ptltool = getToolByName(self.portal, 'portal_cpsportlets', None)
            if self.ptltool is None:
                self.log("CPSPortlets is not installed. Portlets will not be imported")
                LOG("CPS3Importer: CPSPortlets is not installed. Portlets will not be imported",
                    INFO, self.file_path)
            else:
                portlets_els = xpath_findall(root,
                                      "{%s}portlets" % self.ns_uri)
                if portlets_els:
                    self.setupPortlets(self.portal, portlets_els[0])

        for cache in self.portal.portal_trees.objectValues():
            cache.manage_rebuild()


    def buildFolder(self, folder_el, parent_folder):
        """Process the elementtree

        (from XML http://www.nuxeo.com/2004/06/cpshierarchy#folder element)"""

        folder_children_ids = parent_folder.objectIds()
        # build folder
        folder_id = folder_el.get('id')
        if folder_id not in folder_children_ids:
            self.wtool.invokeFactoryFor(parent_folder,
                                        folder_el.get('portal_type'),
                                        folder_id)
        field_els = xpath_findall(xpath_findall(folder_el,
                                                "{%s}datamodel" % self.ns_uri)[0],
                                  "{%s}field" % self.ns_uri)
        # edit folder fields
        if field_els:
            kw = {}
            for field_el in field_els:
                field_name = field_el.get('name')
                field_val = field_el.text
                field_type = field_el.get('type').lower()
                if field_type == 'none':
                    field_val = None
                elif field_type == DateTime.__name__.lower():
                    if field_val:
                        field_val = DateTime(field_val)
                    else:
                        field_val = None
                elif field_type == 'tuple':
                    if field_val == '()':
                        field_val = None
                    else:
                        try:
                            field_val = eval(field_val)
                        except (SyntaxError, ValueError), err:
                            self.log("CPS3Importer: Failed to parse field %s of folder %s: %s" %
                                     (field_name, folder_id, err))
                            LOG("CPS3Importer.HierarchyImporter", ERROR,
                                "Failed to parse field %s of folder %s: %s" %
                                (field_name, folder_id, err))
                elif field_type == 'list':
                    if field_val == '[]':
                        field_val = None
                    else:
                        try:
                            field_val = eval(field_val)
                        except (SyntaxError, ValueError), err:
                            self.log("CPS3Importer: Failed to parse field %s of folder %s: %s" %
                                     (field_name, folder_id, err))
                            LOG("CPS3Importer.HierarchyImporter", ERROR,
                                "Failed to parse field %s of folder %s: %s" %
                                (field_name, folder_id, err))
                elif field_type in ('str', 'string', 'unicode'):
                    if field_val:
                        field_val = toLatin9(field_val)
                    else:
                        field_val = None
                else:
                    if field_val:
                        try:
                            field_val = eval(field_val)
                        except (SyntaxError, ValueError, NameError), err:
                            self.log("CPS3Importer: Failed to parse field %s of folder %s: %s" %
                                     (field_name, folder_id, err))
                            LOG("CPS3Importer.HierarchyImporter", ERROR,
                                "Failed to parse field %s of folder %s: %s" %
                                (field_name, folder_id, err))
                            field_val = None
                    else:
                        field_val = None
                if field_val is not None:
                    kw[field_el.get('name')] = field_val
            folder = getattr(parent_folder, folder_id)
            folder.getEditableContent().edit(proxy=folder, **kw)

            # set some data model fields directly as they have
            # write_ignore_storage set to True and just calling edit() won't
            # do the trick
            def setCreator(creator):
                if getattr(aq_inner(folder), 'creators', None) is not None:
                    # CMF >= 1.5
                    folder.creators = (creator, )
                    folder.getContent().creators = (creator, )
                else:
                    # CMF < 1.5
                    # will require to monkey patch Creator method in DublinCore
                    # to use getOwnerTuple()
                    folder.manage_changeOwnershipType(explicit=1)
                    folder._owner = (folder._owner[0], creator)
                    folder_doc = folder.getContent()
                    folder_doc.manage_changeOwnershipType(explicit=1)
                    folder_doc._owner = (folder_doc._owner[0], creator)
            def setCreationDate(creation_date):
                folder.creation_date = DateTime(creation_date)
                folder.getContent().creation_date = DateTime(creation_date)
            def setModificationDate(modification_date):
                folder.modification_date = DateTime(modification_date)
                folder.getContent().modification_date = DateTime(modification_date)
            actions = {
                'CreationDate' : setCreationDate,
                'ModificationDate' : setModificationDate,
                #'Language' : folder.setLanguage,
                'Format' : folder.setFormat,
                'Creator' : setCreator,
                }
            for action in actions:
                if action in kw:
                    func = actions[action]
                    func(kw[action])

            self.evtool.notifyEvent('modify_object', folder, {})

        # change properties
        props_els = xpath_findall(folder_el,  "{%s}properties/*" % self.ns_uri)
        props = {}
        for prop_el in props_els:
            key = re.sub('{.*}', '', prop_el.tag)
            if key in ('PropDefaultLanguage', 'PropLanguageRevisions'):
                prop_type = prop_el.get('type')
                val = prop_el.text
                # handle case when type is not 'str' or 'string'
                if prop_type in ('dict', 'dictionary'):
                    val = eval(val)
                props[key] = val
        #folder.manage_changeProperties(props)

        #set properties on proxy
        if props:
            if props.has_key('PropDefaultLanguage'):
                folder.setDefaultLanguage(props['PropDefaultLanguage'])
            if props.has_key('PropLanguageRevisions'):
                folder._language_revs = props['PropLanguageRevisions']
            folder.proxyChanged()

        children_els = xpath_findall(folder_el, "{%s}folder" % self.ns_uri)
        # local roles
        if self.restore_local_roles:
            localRoles_els = xpath_findall(folder_el,
                                           "{%s}localRoles" % self.ns_uri)
            if localRoles_els:
                self.setLocalRoles(folder, localRoles_els[0])
        # boxes
        if self.restore_boxes:
            boxes_els = xpath_findall(folder_el,
                                      "{%s}boxes" % self.ns_uri)
            if boxes_els:
                self.setupBoxes(folder, boxes_els[0])

        # portlets
        if self.restore_portlets:
            self.ptltool = getToolByName(self.portal, 'portal_cpsportlets', None)
            if self.ptltool is not None:
                portlets_els = xpath_findall(folder_el,
                                      "{%s}portlets" % self.ns_uri)
                if portlets_els:
                    self.setupPortlets(folder, portlets_els[0])

        # local themes
        if self.restore_local_themes:
            local_themes_els = xpath_findall(folder_el,
                                      "{%s}localthemes" % self.ns_uri)
            if local_themes_els:
                self.setupLocalThemes(
                    folder,
                    local_themes_els[0],
                    '.cpsskins_theme')

        # workflow config
        workflow_chain_els = xpath_findall(folder_el,
                                           "{%s}workflow_chains/{%s}chain" % (self.ns_uri,
                                                                              self.ns_uri))
        if workflow_chain_els:
            self.setupWFConfig(folder, workflow_chain_els)

        for children_el in children_els:
            self.buildFolder(children_el, folder)


    def setLocalRoles(self, folder, localRoles_el):
        """set local roles on folder

        (from XML http://www.nuxeo.com/2004/06/cpshierarchy#localRoles element)"""

        # get usr/roles
        groups = []
        members = []
        for usrRoles_el in xpath_findall(localRoles_el,
                                         "{%s}usrRoles" % self.ns_uri):
            usrid = usrRoles_el.get('usrid')
            roles = usrRoles_el.get('roles').split(',')
            if usrid.startswith('group:'):
                groups.append((usrid[6:], roles))
            elif usrid.startswith('user:'):
                members.append((usrid[5:], roles))
        # reorganise groups and members to optimize calls to setLocal(Group)Roles
        groups_by_roles = {}
        for group in groups:
            for role in group[1]:
                if groups_by_roles.has_key(role):
                    groups_by_roles[role].append(group[0])
                else:
                    groups_by_roles[role] = [group[0]]
        members_by_roles = {}
        for member in members:
            for role in member[1]:
                if members_by_roles.has_key(role):
                    members_by_roles[role].append(member[0])
                else:
                    members_by_roles[role] = [member[0]]
        # assign local roles
        for role, members in members_by_roles.items():
            self.mtool.setLocalRoles(folder, members, role, reindex=0)
        for role, groups in groups_by_roles.items():
            self.mtool.setLocalGroupRoles(folder, groups, role, reindex=0)
        # block local roles (if set)
        blocked_local_roles = booleanParser(localRoles_el.get('blocked_local_roles', '0'))
        if blocked_local_roles:
            self.mtool.setLocalGroupRoles(folder, ('role:Anonymous',), '-',
                                          reindex=0)

        folder.reindexObjectSecurity()

    def setupBoxes(self, folder, boxes_el, idbc='.cps_boxes'):
        """set boxes for folder

        (from XML http://www.nuxeo.com/2004/06/cpshierarchy#boxes element)"""

        box_els = xpath_findall(boxes_el, "{%s}box" % self.ns_uri)
        if box_els:
            boxes = {}
            box_guards = {}
            for box_el in box_els:
                box_id = box_el.get('id')
                props = {'type': box_el.get('boxType')}
                prop_els = xpath_findall(box_el, "{%s}property" % self.ns_uri)
                for prop_el in prop_els:
                    prop_name = prop_el.get('name')
                    prop_val = prop_el.text
                    prop_type = prop_el.get('type')
                    if prop_type == 'str' or prop_type == 'string':
                        props[prop_name] = prop_val or ''
                    elif prop_type == 'list':
                        props[prop_name] = eval(prop_val) or []
                    elif prop_type == 'tuple':
                        props[prop_name] = eval(prop_val) or ()
                    else:
                        try:
                            props[prop_name] = eval(prop_val)
                        except (SyntaxError, ValueError), err:
                            props[prop_name] = prop_val
                            self.log("CPS3Importer: Failed to parse property %s of box %s: %s" %
                                     (prop_name, box_id, err))
                            LOG("CPS3Importer.HierarchyImporter (boxes)", ERROR,
                                "Failed to parse property %s of box %s: %s" %
                                (prop_name, box_id, err))
                boxes[box_id] = props
                guard_els = xpath_findall(box_el, "{%s}guard" % self.ns_uri)
                if guard_els:
                    box_guards[box_id] = self.buildGuard(guard_els[0])

            if idbc in folder.objectIds():
                folder.manage_delObjects([idbc])
            folder.manage_addProduct['CPSDefault'].addBoxContainer()
            bc = getattr(folder, idbc)
            self.verifyBoxes(boxes, bc)
            # set guards on boxes
            for box_id, guard in box_guards.items():
                bc[box_id].setGuardProperties(props=guard)

    def verifyBoxes(self, boxes, box_container):
        ptool = self.portal.portal_types
        for box_id, box_props in boxes.items():
            ptool.constructContent(box_props['type'], box_container, box_id)
            box_container[box_id].manage_changeProperties(**box_props)

    def buildGuard(self, guard_el):
        return {'guard_permissions': guard_el.get('permissions', ''),
                'guard_roles': guard_el.get('roles', ''),
                'guard_expr': guard_el.get('expr', '')}


    def setupPortlets(self, folder, portlets_el):
        """Set up portlets for folder
        """
        portlet_els = xpath_findall(portlets_el, "{%s}portlet" % self.ns_uri)
        if portlet_els:
            if self.ptltool is not None:
                portletimporter = PortletImporter(self.portal, self.file_name, self.dir_name, self.ns_uri)
                portlet_container = self.ptltool.getPortletContainer(
                    context=folder, create=1, local=1)
                portlet_container.manage_delObjects(portlet_container.listPortletIds())
                for portlet_el in portlet_els:
                    portletimporter.buildPortlet(folder, portlet_el, restore_id=0)

    def setupLocalThemes(self, folder, local_themes_el, propid):
        """Setup CPSSkins local themes
        """

        prop_type = local_themes_el.get('type')
        if prop_type not in ('string', 'lines'):
            return

        prop_text = local_themes_el.get('value')
        if prop_type == 'lines':
            prop_value = prop_text.split(',')
        else:
            prop_value = prop_text

        if folder.hasProperty(propid):
            folder.manage_delProperties([propid])
        folder.manage_addProperty(propid, prop_value, prop_type)

    def setupWFConfig(self, folder, wfc_els):
        """set cps_workflow_configuration for folder

        (from XML http://www.nuxeo.com/2004/06/cpshierarchy#workflow_chains element)"""

        chain_els = wfc_els
        if chain_els:
            if hasattr(aq_base(folder), '.cps_workflow_configuration'):
                folder.manage_delObjects(['.cps_workflow_configuration'])
            try:
                folder.manage_addProduct['CPSWorkflow'].addConfiguration()
            except AttributeError:
                # BBB: for older CPS versions
                folder.manage_addProduct['CPSCore'].addCPSWorkflowConfiguration()
            wfc = getattr(folder, '.cps_workflow_configuration')
            for chain_el in chain_els:
                pt = chain_el.get('portal_type')
                value = chain_el.get('value')
                chain_type = chain_el.get('type')
                if chain_type == 'local':
                    wfc.manage_addChain(portal_type=pt, chain=value)
                elif chain_type == 'below':
                    wfc.manage_addChain(portal_type=pt, chain=value, under_sub_add=1)
                else:
                    self.log("CPS3Importer: Bad value for workflow chain type: %s in folder %s. Authorized values are 'local' and 'below'." % (chain_type, folder.absolute_url(relative=1)))
                    LOG("CPS3Importer.HierarchyImporter", ERROR,
                        "Bad value for workflow chain type: %s in folder %s. Authorized values are 'local' and 'below'." % (chain_type, folder.absolute_url(relative=1)))


#
# CPS 3 Workflow Importer
#
class WorkflowImporter(IOBase):

    def __init__(self, portal, file_name, dir_name):
        self.portal = portal
        self.wtool = self.portal.portal_workflow
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name, self.file_name)
        self.ns_uri = main_namespace_uri + 'cpsworkflows#'
        self.elementtree_ns_uri = "{%s}" % self.ns_uri
        # adding 2 for surrounding curly braces {} of James Clark's NS syntax
        self.ns_uri_len = len(self.ns_uri) + 2

    def importFile(self):
        """Parse the XML file into an elementtree structure"""

        self.log("Importing workflows from file " + self.file_path)
        LOG("Importing workflows from file", INFO, self.file_path)

        doc = ElementTree(file=self.file_path)
        self.updateWorkflows(doc.getroot())

    def updateWorkflows(self, root):
        """Process the elementtree"""

        # get transition behavior mapping
        # this is just for robustness in case constant values change between
        # the versions of CMF/CPS used to import/export workflows
        self.TRANSITION_BEHAVIORS = {}
        try:
            from Products.CPSWorkflow import workflow as CPSWorkflow
        except ImportError, e:
            if 'No module named CPSWorkflow' not in str(e):
                raise
            # BBB: for older CPS versions
            from Products.CPSCore import CPSWorkflow
        for tb_el in xpath_findall(xpath_findall(root,
                                                 "{%s}transitionBehaviors" % self.ns_uri)[0],
                                   "{%s}transitionBehavior" % self.ns_uri):
            self.TRANSITION_BEHAVIORS[tb_el.get('ref')] = getattr(CPSWorkflow, tb_el.get('name'))

        # get trigger type mapping
        self.TRIGGER_TYPES = {}
        from Products.DCWorkflow import Transitions
        for tt_el in xpath_findall(xpath_findall(root,
                                                 "{%s}triggerTypes" % self.ns_uri)[0],
                                   "{%s}triggerType" % self.ns_uri):
            self.TRIGGER_TYPES[tt_el.get('ref')] = getattr(Transitions, tt_el.get('name'))

        # get workflow definitions
        for wf_el in xpath_findall(xpath_findall(root,
                                                 "{%s}workflowDefinitions" % self.ns_uri)[0],
                                   "{%s}workflow" % self.ns_uri):
            self.buildWorkflow(wf_el)

        # set global chains
        for chain_el in xpath_findall(xpath_findall(root,
                                                 "{%s}globalChains" % self.ns_uri)[0],
                                   "{%s}globalChain" % self.ns_uri):
            self.wtool.setChainForPortalTypes([chain_el.get('portal_type')],
                                              chain_el.get('chain'))

    def buildWorkflow(self, el):
        """Build a CPS Workflow

        (from XML http://www.nuxeo.com/2004/06/cpsworkflows#workflow element)"""

        # workflow definiton
        wfdef = {'wfid': el.get('id'),
                 'title': toLatin9(el.get('title'))}
        state_var = el.get('state_variable', None)
        if state_var is not None:
            wfdef['state_var'] = state_var
        permissions = el.get('permissions', None)
        if permissions is not None:
            permissions_tuple = ()
            for permission in permissions.split(','):
                permissions_tuple += (permission.strip(), )
            wfdef['permissions'] = permissions_tuple

        # states
        states = self.getWorkflowStates(xpath_findall(el,
                                                      "{%s}states" % self.ns_uri)[0])
        # transitions
        transitions = self.getWorkflowTransitions(xpath_findall(el,
                                                                "{%s}transitions" % self.ns_uri)[0])
        # scripts
        scripts = self.getWorkflowScripts(xpath_findall(el,
                                                        "{%s}scripts" % self.ns_uri)[0])
        # variables
        variables = self.getWorkflowVariables(xpath_findall(el,
                                                            "{%s}variables" % self.ns_uri)[0])

        self.verifyWorkflow(wfdef, states, transitions,
                            scripts, variables)


    def getWorkflowStates(self, el):
        """Build a CPS Workflow's states

        (from XML http://www.nuxeo.com/2004/06/cpsworkflows#states element)"""

        states = {}
        for state_el in xpath_findall(el, "{%s}state" % self.ns_uri):
            data = {}
            data['title'] = toLatin9(state_el.get('title'))
            data['description'] = toLatin9(state_el.get('description', ''))
            transitions = ()
            transitions_attr = state_el.get('allowedTransitions')
            if transitions_attr:
                for transition in transitions_attr.split(','):
                    transitions += (transition.strip(),)
            data['transitions'] = transitions
            data['permissions'] = {}
            permissions_els = xpath_findall(state_el, "{%s}permissions" % self.ns_uri)
            if len(permissions_els) > 0:
                permission_els = xpath_findall(permissions_els[0], "{%s}permission" % self.ns_uri)
                if len(permission_els) > 0:
                    permissions = {}
                    for permission_el in permission_els:
                        roles_attr = permission_el.get('roles')
                        if not booleanParser(permission_el.get('acquired')) and roles_attr:
                            roles = ()
                            for role in roles_attr.split(','):
                                roles += (role.strip(),)
                            permissions[permission_el.get('title')] = roles
                    if permissions:
                        data['permissions'] = permissions
            states[state_el.get('id')] = data
        return states

    def getWorkflowTransitions(self, el):
        """Build a CPS Workflow's transitions

        (from XML http://www.nuxeo.com/2004/06/cpsworkflows#transitions element)"""

        transitions = {}
        for transition_el in xpath_findall(el, "{%s}transition" % self.ns_uri):
            data = {}
            for attr_name in ( 'title',):
                attr_val = transition_el.get(attr_name, None)
                if attr_val is not None:
                    data[attr_name] = toLatin9(attr_val)
            for attr_name in ('new_state_id',):
                attr_val = transition_el.get(attr_name, None)
                if attr_val is not None:
                    data[attr_name] = attr_val
            for attr_name in ('description', 'actbox_name'):
                attr_val = transition_el.get(attr_name, None)
                if attr_val is not None:
                    data[attr_name] = toLatin9(attr_val)
            for attr_name in ('script_name', 'after_script_name',
                              'actbox_url'):
                attr_val = transition_el.get(attr_name, None)
                if attr_val is not None:
                    data[attr_name] = attr_val
            for attr_name in ('actbox_category',):
                # special treatment for actbox_category as
                # DCWorkflow.setProperties defaults its value
                # to 'workflow' if None ; we do not want that
                # to happen : '' shoud be '', not 'workflow'
                attr_val = transition_el.get(attr_name, None)
                if attr_val is not None:
                    data[attr_name] = attr_val
                else:
                    data[attr_name] = ''
            for attr_name in ('clone_allowed_transitions',
                              'checkout_allowed_initial_transitions',
                              'checkin_allowed_transitions'):
                attr_val = transition_el.get(attr_name, None)
                if attr_val:
                    val = ()
                    for token in attr_val.split(','):
                        val += (token.strip(),)
                    if val:
                        data[attr_name] = val
                    else:
                        data[attr_name] = None
                else:
                    data[attr_name] = None
            # transition behaviors
            data['transition_behavior'] = ()
            tb_attr = transition_el.get('transition_behavior', None)
            if tb_attr is not None:
                tb_tuple = ()
                for tb in tb_attr.split(','):
                    tb_tuple += (self.TRANSITION_BEHAVIORS.get(tb.strip()),)
                if tb_tuple:
                    data['transition_behavior'] = tb_tuple
            # trigger type
            tt_attr = transition_el.get('trigger_type', None)
            if tt_attr is not None:
                tb_int = self.TRIGGER_TYPES.get(tt_attr)
                if tb_int is not None:
                    data['trigger_type'] = tb_int
            # guard
            guard_els = xpath_findall(transition_el, "{%s}guard" % self.ns_uri)
            if len(guard_els) > 0:
                # the schema allows at most one such element
                guard_el = guard_els[0]
                roles = guard_el.get('roles', None)
                permissions = guard_el.get('permissions', None)
                expr = guard_el.get('expr', None)
                data['props'] = {'guard_permissions': '',
                                 'guard_roles': '',
                                 'guard_expr': ''}
                if (permissions is not None):
                    data['props']['guard_permissions'] = permissions
                if (roles is not None):
                    data['props']['guard_roles'] = roles
                if (expr is not None):
                    data['props']['guard_expr'] = expr
            transitions[transition_el.get('id')] = data
        return transitions

    def getWorkflowScripts(self, el):
        """Build a CPS Workflow's scripts

        (from XML http://www.nuxeo.com/2004/06/cpsworkflows#scripts element)"""

        scripts = {}
        for script_el in xpath_findall(el, "{%s}script" % self.ns_uri):
            data = {}
            _owner = script_el.get('owner', None)
            data['_owner'] = _owner
            proxy_roles_attr = script_el.get('proxy_roles', None)
            if proxy_roles_attr:
                proxy_roles = ()
                for role in proxy_roles_attr.split(','):
                    proxy_roles += (role.strip(),)
                if proxy_roles:
                    data['_proxy_roles'] = proxy_roles
            data['script'] = xpath_findall(script_el, "{%s}code" % self.ns_uri)[0].text
            scripts[script_el.get('id')] = data
        return scripts

    def getWorkflowVariables(self, el):
        """Build a CPS Workflow's variables

        (from XML http://www.nuxeo.com/2004/06/cpsworkflows#variables element)"""

        variables = {}
        for variable_el in xpath_findall(el, "{%s}variable" % self.ns_uri):
            data = {}
            data['update_always'] = booleanParser(variable_el.get('always_update'))
            data['for_status'] = booleanParser(variable_el.get('storeInWorkflowStatus'))
            data['for_catalog'] = booleanParser(variable_el.get('availableToCatalog'))
            data['description'] = toLatin9(variable_el.get('description'))
            defaultValue_els = xpath_findall(variable_el,
                                             "{%s}defaultValue" % self.ns_uri)
            # default value
            if len(defaultValue_els) > 0:
                # the schema allows at most one such element
                defaultValue_el = defaultValue_els[0]
                if defaultValue_el.text:
                    data['default_value'] = defaultValue_el.text
            defaultExpression_els = xpath_findall(variable_el,
                                                  "{%s}defaultExpression" % self.ns_uri)
            # default expression
            if len(defaultExpression_els) > 0:
                # the schema allows at most one such element
                defaultExpression_el = defaultExpression_els[0]
                if defaultExpression_el.text:
                    data['default_expr'] = defaultExpression_el.text
            # guard
            guard_els = xpath_findall(variable_el, "{%s}guard" % self.ns_uri)
            if len(guard_els) > 0:
                # the schema allows at most one such element
                guard_el = guard_els[0]
                roles = guard_el.get('roles', None)
                permissions = guard_el.get('permissions', None)
                expr = guard_el.get('expr', None)
                data['props'] = {'guard_permissions': '',
                                 'guard_roles': '',
                                 'guard_expr': ''}
                if (permissions is not None):
                    data['props']['guard_permissions'] = permissions
                if (roles is not None):
                    data['props']['guard_roles'] = roles
                if (expr is not None):
                    data['props']['guard_expr'] = expr

            variables[variable_el.get('id')] = data
        return variables

    #
    # Workflow update methods (inspired by CPSInstaller's)
    #

    def verifyWorkflow(self, wfdef={}, states={}, transitions={},
                       scripts={}, variables={}):

        wf = self.createWorkflow(wfdef)
        if wf is None:
            return

        self.verifyWfStates(wf, states)
        self.verifyWfTransitions(wf, transitions)
        self.verifyWfScripts(wf, scripts)
        self.verifyWfVariables(wf, variables,
                               state_var=wfdef.get('state_var'))

    def createWorkflow(self, wfdef):
        wfid = wfdef['wfid']

        if wfid not in self.wtool.objectIds():
            self.wtool.manage_addWorkflow(id=wfid,
                                          workflow_type='cps_workflow (Web-configurable workflow for CPS)')

        wf = self.wtool[wfid]
        wf.title = wfdef['title']
        if hasattr(wf, 'isUserModified') and wf.isUserModified():
            self.log("CPS3Importer: WARNING: The workflow permissions are modified and will not be changed. Delete manually if needed.")
            LOG('CPS3Importer.WorkflowImporter',
                DEBUG,
                'WARNING: The workflow permissions are modified and will not be changed. Delete manually if needed.')
            return wf

        wf.permissions = ()
        if wfdef.has_key('permissions'):
            for p in wfdef['permissions']:
                wf.addManagedPermission(p)
        return wf

    def verifyWfStates(self, workflow, states):
        existing_states = workflow.states.objectIds()
        for stateid, statedef in states.items():
            if stateid in existing_states:
                ob = workflow.states[stateid]
                if hasattr(ob, 'isUserModified') and ob.isUserModified():
                    self.log("CPS3Importer: WARNING: The workflow state is modified and will not be changed. Delete manually if needed.")
                    LOG('CPS3Importer.WorkflowImporter',
                        DEBUG,
                        'WARNING: The workflow state is modified and will not be changed. Delete manually if needed.')
                    continue
                else:
                    workflow.states.manage_delObjects([stateid])
            workflow.states.addState(stateid)
            state = workflow.states.get(stateid)
            state.setProperties(title=statedef['title'],
                                transitions=statedef['transitions'],
                                description=statedef['description'])
            for permission in statedef['permissions'].keys():
                state.setPermission(permission, 0,
                                    statedef['permissions'][permission])

    def verifyWfTransitions(self, workflow, transitions):
        existing_transitions = workflow.transitions.objectIds()
        for transid, transdef in transitions.items():
            if transid in existing_transitions:
                ob = workflow.transitions[transid]
                if hasattr(ob, 'isUserModified') and ob.isUserModified():
                    self.log("CPS3Importer: WARNING: The workflow transition is modified and will not be changed. Delete manually if needed.")
                    LOG('CPS3Importer.WorkflowImporter',
                        DEBUG,
                        'WARNING: The workflow transition is modified and will not be changed. Delete manually if needed.')
                    continue
                else:
                    workflow.transitions.manage_delObjects([transid])
            workflow.transitions.addTransition(transid)
            trans = workflow.transitions.get(transid)
            trans.setProperties(**transdef)

    def verifyWfScripts(self, workflow, scripts):
        existing_scripts = workflow.scripts.objectIds()
        for scriptid, scriptdef in scripts.items():
            if scriptid in existing_scripts:
                ob = workflow.scripts[scriptid]
                if hasattr(ob, 'isUserModified') and ob.isUserModified():
                    self.log("CPS3Importer: WARNING: The workflow script is modified and will not be changed. Delete manually if needed.")
                    LOG('CPS3Importer.WorkflowImporter',
                        DEBUG,
                        'WARNING: The workflow script is modified and will not be changed. Delete manually if needed.')
                    continue
                else:
                    workflow.scripts.manage_delObjects([scriptid])
            workflow.scripts._setObject(scriptid, PythonScript(scriptid))
            script = workflow.scripts[scriptid]
            script.write(scriptdef['script'])
            for attribute in ('title', '_proxy_roles', '_owner'):
                if scriptdef.has_key(attribute):
                    setattr(script, attribute, scriptdef[attribute])

    def verifyWfVariables(self, workflow, variables, state_var=None):
        existing_vars = workflow.variables.objectIds()
        for varid, vardef in variables.items():
            if varid in existing_vars:
                ob = workflow.variables[varid]
                if hasattr(ob, 'isUserModified') and ob.isUserModified():
                    self.log("CPS3Importer: WARNING: The workflow variable is modified and will not be changed. Delete manually if needed.")
                    LOG('CPS3Importer.WorkflowImporter',
                        DEBUG,
                        'WARNING: The workflow variable is modified and will not be changed. Delete manually if needed.')
                    continue
                else:
                    workflow.variables.manage_delObjects([varid])
            workflow.variables.addVariable(varid)
            var = workflow.variables[varid]
            var.setProperties(**vardef)

        if state_var:
            if (hasattr(workflow.variables, 'isUserModified')
                and workflow.variables.isUserModified()):
                self.log("CPS3Importer: WARNING: The workflow state variable is modified and will not be changed. Change manually if needed.")
                LOG('CPS3Importer.WorkflowImporter',
                    DEBUG,
                    'WARNING: The workflow state variable is modified and will not be changed. Change manually if needed.')
            else:
                workflow.variables.setStateVar(state_var)


#
# CPS 3 Documents Importer
#
class DocumentImporter(IOBase):

    def __init__(self, portal, file_name, dir_name, ido):
        self.portal = portal
        self.repository = self.portal.portal_repository
        self.pxtool = self.portal.portal_proxies
        self.pttool = self.portal.portal_types
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name, self.file_name)
        self.ns_uri = main_namespace_uri + 'cpsdocument#'
        self.elementtree_ns_uri = "{%s}" % self.ns_uri
        # adding 2 for surrounding curly braces {} of James Clark's NS syntax
        self.ns_uri_len = len(self.ns_uri) + 2
        self.overwrite_existing_docs = ido
        self.doc_ids_to_replace = {}
        self.wf_history4proxy = {}
        self.workflow_attr_names = ('action', 'actor', 'dest_container', 'review_state',
                                    'time', 'time_str', 'workflow_id', 'rpath', 'state')
        # Check if CPSForum is installed
        self.map_docs_to_comments = False
        dtool = getToolByName(self.portal, 'portal_discussion', None)
        if dtool is not None and dtool.meta_type == 'CPS Discussion Tool':
            self.map_docs_to_comments = True

    def importFile(self):
        """Parse the XML file into an elementtree structure"""

        self.log("Importing documents from file " + self.file_path)
        LOG("Importing documents from file", INFO, self.file_path)

        doc = ElementTree(file=self.file_path)
        root = doc.getroot()
        document_els = xpath_findall(root, "{%s}document" % self.ns_uri)
        self.proxyList = []
        nb_docs = len(document_els)
        i = 0
        for document_el in document_els:
            i += 1
            if i == 1 or i % 20 == 0:
                if i + 20 > nb_docs:
                    j = nb_docs
                else:
                    j = i + 20
                self.log('CPS3 DocumentImporter: '
                         'Processing documents [%s-%s] of %s' \
                         % (str(i), str(j), str(nb_docs)))

            LOG('CPS3 DocumentImporter:', DEBUG,
                'Processing document %s' % document_el.get('id'))
            self.buildRepositoryDocument(document_el)
            LOG('CPS3 DocumentImporter:', DEBUG,
                'Processed document %s' % document_el.get('id'))
            # make subtransaction every SUBTRANSACTION_COMMIT object
            # to free memory.
            if i % SUBTRANSACTION_COMMIT == 0:
                get_transaction().commit(1)
                LOG("CPS3 DocumentImporter:", DEBUG,
                    "subtransaction commit - %dth element" % i)

            self.buildProxyList(document_el)
        self.buildAllProxies()
        #XXX: will we need to do that? proxies are not linked to documents
        #     in repository right now (documents in repo are considered orphans)
        for cache in self.portal.portal_trees.objectValues():
            cache.manage_rebuild()

    def buildRepositoryDocument(self, document_el):
        """Build a CPS Document

        (from XML http://www.nuxeo.com/2004/06/cpsdocument#document element)"""

        doc_id = document_el.get('id')
        portal_type = document_el.get('portalType')
        # if doc_id is already in use, create a new one (and remember it
        # so that proxies get it too)
        if doc_id in self.repository.objectIds():
            if self.overwrite_existing_docs:
                self.repository.manage_delObjects([doc_id])
            else:
                old_doc_id = doc_id[:doc_id.find('_')]
                free_id = self.repository.getFreeDocid()
                doc_id = free_id + '__0001'
                self.doc_ids_to_replace[old_doc_id] = free_id

        # first put the document in the repository
        self.repository.constructContent(portal_type, doc_id)
        doc = self.repository.get(doc_id)
        # then add flexible information (if any): schemas and layouts
        fake_schema_importer = SchemaImporter(self.portal, '', '')
        schema_els = xpath_findall(document_el,
                                   "{%s}flexibleSchemas/{%s}schema" % (self.ns_uri,
                                                                       fake_schema_importer.ns_uri))
        if len(schema_els) > 0:
            if not hasattr(aq_base(doc), '.cps_schemas'):
                schemas = SchemaContainer('.cps_schemas')
                doc._setObject(schemas.getId(), schemas)
            schema_container = doc._getOb('.cps_schemas')
            self.buildFlexibleSchemas(schema_container, schema_els, fake_schema_importer)


        fake_layout_importer = LayoutImporter(self.portal, '', '')
        layout_els = xpath_findall(document_el,
                                   "{%s}flexibleLayouts/{%s}layout" % (self.ns_uri,
                                                                       fake_layout_importer.ns_uri))
        if len(layout_els) > 0:
            if not hasattr(aq_base(doc), '.cps_layouts'):
                layouts = LayoutContainer('.cps_layouts')
                doc._setObject(layouts.getId(), layouts)
            layout_container = doc._getOb('.cps_layouts')
            self.buildFlexibleLayouts(layout_container, layout_els, fake_layout_importer)
        # then retrieve field values and update document's datamodel
        kw = {}
        for field_el in xpath_findall(document_el, "{%s}dataModel/{%s}field" %
                                      (self.ns_uri, self.ns_uri)):
            val_type = field_el.get('type')
            if val_type == 'NoneType' or val_type == 'None':
                val = None
            elif val_type == 'str' or val_type == 'string':
                val = toLatin9(field_el.text) or ''
            elif val_type == 'DateTime':
                val = DateTime(field_el.text)
            elif val_type == 'instance':
                val = field_el.text or None
            elif val_type == 'Image':
                id = field_el.get('file_name')
                title = field_el.get('title')
                title = toLatin9(title) or ''
                content_type = field_el.get('contentType', '')
                data_file_rpath = field_el.get('ref')
                data_file_rpath = toLatin9(data_file_rpath)
                data_file_path = os.path.join(CLIENT_HOME, self.dir_name, data_file_rpath)
                data_file = open(data_file_path, 'rb')
                val = Image(id, title, data_file, content_type=content_type)
            elif val_type == 'File':
                id = toLatin9(field_el.get('file_name'))
                title = field_el.get('title')
                title = toLatin9(title) or ''
                content_type = field_el.get('contentType', '')
                data_file_rpath = field_el.get('ref')
                data_file_rpath = toLatin9(data_file_rpath)
                data_file_path = os.path.join(CLIENT_HOME, self.dir_name, data_file_rpath)
                data_file = open(data_file_path, 'rb')
                val = File(id, title, data_file, content_type=content_type)
            else:
                val = eval(field_el.text)
            kw[field_el.get('id')] = val
        doc.edit(**kw)
        # set some data model fields directly as they have write_ignore_storage
        # set to True and just calling edit() won't do the trick
        def setCreator(creator):
            if getattr(aq_inner(doc), 'creators', None) is not None:
                # CMF >= 1.5
                doc.creators = (creator, )
            else:
                # CMF < 1.5
                # will require to monkey patch Creator method in DublinCore
                # to use getOwnerTuple()
                doc.manage_changeOwnershipType(explicit=1)
                doc._owner = (doc._owner[0], creator)
        def setCreationDate(creation_date):
            doc.creation_date = DateTime(creation_date)
        def setModificationDate(modification_date):
            doc.modification_date = DateTime(modification_date)
        actions = {'CreationDate' : setCreationDate,
                   'ModificationDate' : setModificationDate,
                   'Language' : doc.setLanguage,
                   'Format' : doc.setFormat,
                   'Creator' : setCreator,
                   }
        for action in actions:
            if action in kw:
                func = actions[action]
                func(kw[action])

        is_frozen = kw.get('_cps_frozen')
        if is_frozen is not None:
            doc._cps_frozen = is_frozen

        self.buildDocumentWorkflowHistory(doc_id, document_el)

    def buildFlexibleSchemas(self, schema_container, schema_els,
                             fake_schema_importer):
        """Build schemas from their XML representation"""

        schemas = {}
        for el in schema_els:
            schema_def = SchemaImporter.buildSchema(fake_schema_importer, el)
            if schema_def:
                id = schema_def.get('_id')
                del schema_def['_id']
                schemas[id] = schema_def
        SchemaImporter.verifySchemas(fake_schema_importer, schemas,
                                     schema_container=schema_container)

    def buildFlexibleLayouts(self, layout_container, layout_els,
                             fake_layout_importer):
        """Build layouts from their XML representation"""

        layouts = {}
        for el in layout_els:
            layout_def = LayoutImporter.buildLayout(fake_layout_importer, el)
            if layout_def:
                id = layout_def.get('_id')
                del layout_def['_id']
                layouts[id] = layout_def
        LayoutImporter.verifyLayouts(fake_layout_importer, layouts,
                                     layout_container=layout_container)

    def buildDocumentWorkflowHistory(self, doc_id, document_el):
        history = ()
        for workflowEvent_el in xpath_findall(document_el,
                                              "{%s}history/{%s}workflowEvent" % (self.ns_uri,
                                                                                 self.ns_uri)):
            event = {}
            rpath = workflowEvent_el.get('rpath')
            event['rpath'] = rpath
            for attrib in ('action', 'actor', 'dest_container', 'review_state',
                           'time_str', 'workflow_id', 'state', 'rpath'):
                val = workflowEvent_el.get(attrib, '')
                event[attrib] = val
            time_attr = workflowEvent_el.get('time')
            if time_attr is not None:
                event['time'] = DateTime(time_attr)
            # process other "unknown" attributes for robustness (issue a warning)
            all_other_attr_names = [name for name in workflowEvent_el.keys()
                                    if name not in self.workflow_attr_names]
            for attrib in all_other_attr_names:
                val = workflowEvent_el.get(attrib, '')
                self.log("DocumentImporter: document workflow history: unknown workflow event attribute " + attrib + "=" + val + " for document " + doc_id)
                LOG('DocumentImporter: document workflow history: unknown workflow event attribute',
                    WARNING, attrib + '=' + val + ' for document ' + doc_id)
                event[attrib] = val
            comments_els = xpath_findall(workflowEvent_el, "{%s}comments" % self.ns_uri)
            if len(comments_els) > 0:
                event['comments'] = toLatin9(comments_els[0].text) or ''
            else:
                event['comments'] = ''
            langRev_els = xpath_findall(workflowEvent_el, "{%s}language_revs" % self.ns_uri)
            if len(langRev_els) > 0:
                language_revisions = {}
                for langRevAttr in langRev_els[0].items():
                    language_revisions[langRevAttr[0]] = int(langRevAttr[1])
                event['language_revs'] = language_revisions
            history += (event,)
            # remember data for setting proxy.workflow_history
            if rpath in self.wf_history4proxy.keys():
                self.wf_history4proxy[rpath] += (event,)
            else:
                self.wf_history4proxy[rpath] = (event,)
        self.repository.setHistory(doc_id[:doc_id.find('_')], history)

    def buildProxyList(self, document_el):
        for proxy_el in xpath_findall(document_el, "{%s}proxy" % self.ns_uri):
            rpath = proxy_el.get('rpath')
            portal_type = document_el.get('portalType')
            self.proxyList.append((rpath, proxy_el, portal_type))

    def buildAllProxies(self):
        # first sort proxies so that containers are instantiated
        # before their content
        self.proxyList.sort(proxySorter)
        for proxy in self.proxyList:
            self.buildProxy(proxy[1], proxy[0], proxy[2])

    def buildProxy(self, proxy_el, rpath, portal_type):
        # prepare proxy properties
        default_language = proxy_el.get('defaultLang', None)
        doc_id = proxy_el.get('docId')
        if self.doc_ids_to_replace.has_key(doc_id):
            # doc_id might alreaby be in use ; in this case a new doc_id
            # has been created for the imported document
            doc_id = self.doc_ids_to_replace.get(doc_id)
        language_revisions = {}
        langRev_els = xpath_findall(proxy_el, "{%s}languageRevisions" % self.ns_uri)
        if len(langRev_els) > 0:
            for langRevAttr in langRev_els[0].items():
                language_revisions[langRevAttr[0]] = int(langRevAttr[1])
        from_language_revisions = {}
        flangRev_els = xpath_findall(proxy_el, "{%s}fromLanguageRevisions" % self.ns_uri)
        if len(flangRev_els) > 0:
            for flangRevAttr in flangRev_els[0].items():
                 from_language_revisions[flangRevAttr[0]] = int(flangRevAttr[1])
        # actually create the proxy
        rpath_items = rpath.split('/')
        if len(rpath_items) > 1:
            proxy_id = rpath_items[-1]
            parent_path = '/'.join(rpath_items[:-1])
        else:
            proxy_id = rpath
            parent_path = None
        if parent_path is not None:
            container = self.portal.restrictedTraverse(parent_path)
        else:
            container = self.portal
        proxy_type = getattr(self.pttool, portal_type).cps_proxy_type
        if proxy_id in container.objectIds():
            if self.overwrite_existing_docs:
                # if proxy_id already exists, replace it
                container.manage_delObjects([proxy_id])
            else:
                # if proxy_id already exists, create a new non-conflicting one
                proxy_id = self.portal.computeId(compute_from=proxy_id,
                                                 location=container)
        proxy = self.pxtool.createEmptyProxy(proxy_type ,container,
                                             portal_type, proxy_id,
                                             docid=doc_id)
        #set properties on proxy
        proxy.setDefaultLanguage(default_language)
        for lang, rev in language_revisions.items():
            proxy.setLanguageRevision(lang, rev)
        proxy.setFromLanguageRevisions(from_language_revisions)

        doc = proxy.getContent()
        # 'creators' are for CMF1.5+
        try:
            proxy.creators = doc.listCreators()
        except AttributeError:
            # CMF < 1.5
            # will require to monkey patch Creator method in DublinCore
            # to use getOwnerTuple()
            proxy.manage_changeOwnershipType(explicit=1)
            #proxy._owner = (proxy._owner[0], doc.Creator())
            proxy._owner = (proxy._owner[0], doc.getOwnerTuple()[1])
        proxy.creation_date = doc.creation_date
        proxy.setModificationDate(doc.ModificationDate())
        proxy.setFormat(doc.Format())


        # set proxy permissions
        permissions = []
        for permission_el in xpath_findall(proxy_el,
                                           "{%s}permissions/{%s}permission" %
                                           (self.ns_uri, self.ns_uri)):
            acquired = booleanParser(permission_el.get('acquired', '1'))
            perm_name = permission_el.get('name')
            perm_roles = [role for role in permission_el.get('roles').split(',')]
            permissions.append((perm_name, acquired, perm_roles))
        # set the permissions
        for permission in permissions:
            proxy.manage_permission(permission[0], acquire=permission[1],
                                    roles=permission[2])
        # restore workflow history
        if self.wf_history4proxy.has_key(rpath):
            events = self.wf_history4proxy.get(rpath)
            history = {}
            for event in events:
                wf_id = event['workflow_id']
                if history.has_key(wf_id):
                    history[wf_id] += (event,)
                else:
                    history[wf_id] = (event,)
            has_history = 0
            if hasattr(aq_base(proxy), 'workflow_history'):
                history = proxy.workflow_history
                if history is not None:
                    has_history = 1
            if not has_history:
                proxy.workflow_history = PersistentMapping()
            for wf_events in history.items():
                proxy.workflow_history[wf_events[0]] = wf_events[1]
        # notify changes made on proxy
        proxy.proxyChanged()
        # associate comments with document proxy
        if self.map_docs_to_comments:
            comment_forum_url = proxy_el.get('commentForum', None)
            if comment_forum_url:
                comment_forum_url = self.portal.id + '/' + comment_forum_url
                relative_url = self.portal.id + '/' + rpath
                self.portal.portal_discussion.registerCommentForum(
                    proxy_path=relative_url,
                    forum_path=comment_forum_url)


    def buildPortlet(self, folder, portlet_el, restore_id=0):
        """Build a CPS Portlet
        """
        ptltool = getToolByName(self.portal, 'portal_cpsportlets')
        container = ptltool.getPortletContainer(context=folder)
        portlet_id = portlet_el.get('id')
        portlet_type = portlet_el.get('portletType')
        # first create a portlet in the container
        kw = {'ptype_id': portlet_type,
              'context': folder}
        if restore_id:
            kw['identifier'] = portlet_id
            if portlet_id in container.objectIds():
                container.manage_delObjects([portlet_id])
        new_portlet_id = ptltool.createPortlet(**kw)
        portlet = container.getPortletById(new_portlet_id)
        if portlet is None:
            self.log("CPS3Importer: Failed to import %s of type %s in %s" %
                     (new_portlet_id, portlet_type, self.portal.portal_url.getRelativeUrl(container)))
            return
        # then add flexible information (if any): schemas and layouts
        fake_schema_importer = SchemaImporter(self.portal, '', '')
        schema_els = xpath_findall(portlet_el,
                                   "{%s}flexibleSchemas/{%s}schema" % (self.ns_uri,
                                                                       fake_schema_importer.ns_uri))
        if len(schema_els) > 0:
            if not hasattr(aq_base(portlet), '.cps_schemas'):
                schemas = SchemaContainer('.cps_schemas')
                portlet._setObject(schemas.getId(), schemas)
            schema_container = portlet._getOb('.cps_schemas')
            self.buildFlexibleSchemas(schema_container, schema_els, fake_schema_importer)


        fake_layout_importer = LayoutImporter(self.portal, '', '')
        layout_els = xpath_findall(portlet_el,
                                   "{%s}flexibleLayouts/{%s}layout" % (self.ns_uri,
                                                                       fake_layout_importer.ns_uri))
        if len(layout_els) > 0:
            if not hasattr(aq_base(portlet), '.cps_layouts'):
                layouts = LayoutContainer('.cps_layouts')
                portlet._setObject(layouts.getId(), layouts)
            layout_container = portlet._getOb('.cps_layouts')
            self.buildFlexibleLayouts(layout_container, layout_els, fake_layout_importer)
        # then retrieve field values and update portlet's datamodel
        kw = {}
        for field_el in xpath_findall(portlet_el, "{%s}dataModel/{%s}field" %
                                      (self.ns_uri, self.ns_uri)):
            val_type = field_el.get('type')
            if val_type == 'NoneType' or val_type == 'None':
                val = None
            elif val_type == 'str' or val_type == 'string':
                val = toLatin9(field_el.text) or ''
            elif val_type == 'instance':
                val = field_el.text or None
            elif val_type == 'Image':
                id = field_el.get('file_name')
                title = field_el.get('title')
                title = toLatin9(title) or ''
                content_type = field_el.get('contentType', '')
                data_file_rpath = field_el.get('ref')
                data_file_rpath = toLatin9(data_file_rpath)
                data_file_path = os.path.join(CLIENT_HOME, self.dir_name, data_file_rpath)
                data_file = open(data_file_path, 'rb')
                val = Image(id, title, data_file, content_type=content_type)
            elif val_type == 'File':
                id = field_el.get('file_name')
                title = field_el.get('title') or ''
                content_type = field_el.get('contentType', '')
                data_file_rpath = field_el.get('ref')
                data_file_rpath = toLatin9(data_file_rpath)
                data_file_path = os.path.join(CLIENT_HOME, self.dir_name, data_file_rpath)
                data_file = open(data_file_path, 'rb')
                val = File(id, title, data_file, content_type=content_type)
            elif val_type == DateTime.__name__:
                val = DateTime(field_el.text)
            else:
                val = eval(field_el.text)
            kw[field_el.get('id')] = val
        portlet.edit(**kw)
        # portlet guard
        guard_els = xpath_findall(portlet_el, "{%s}guard" % self.ns_uri)
        if guard_els:
            guard = self.buildGuard(guard_els[0])
            portlet.setGuardProperties(props=guard)
        # set Language manually as doing it through edit() does not do it
        if kw.has_key('Language'):
            portlet.setLanguage(kw['Language'])

#
# CPS 3 Portlet Importer
#
class PortletImporter(IOBase, DocumentImporter):

    def __init__(self, portal, file_name, dir_name, ns_uri):
        self.portal = portal
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name, self.file_name)
        self.ns_uri = ns_uri
        self.elementtree_ns_uri = "{%s}" % self.ns_uri
        # adding 2 for surrounding curly braces {} of James Clark's NS syntax
        self.ns_uri_len = len(self.ns_uri) + 2

    def buildGuard(self, guard_el):
        return {'guard_permissions': guard_el.get('permissions', ''),
                'guard_roles': guard_el.get('roles', ''),
                'guard_groups': guard_el.get('groups', ''),
                'guard_expr': guard_el.get('expr', '')}

#
# CPSSkins Theme Settings Importer
#
class ThemeSettingsImporter(IOBase):

    def __init__(self, portal, file_name, dir_name):
        self.portal = portal
        self.tmtool = getToolByName(portal, 'portal_themes', None)
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name, self.file_name)
        self.ns_uri = main_namespace_uri + 'themesettings#'
        self.elementtree_ns_uri = "{%s}" % self.ns_uri
        # adding 2 for surrounding curly braces {} of James Clark's NS syntax
        self.ns_uri_len = len(self.ns_uri) + 2

    def importFile(self):
        """Parse the XML file into an elementtree structure"""

        container = self.tmtool
        if container is None:
            self.log("CPS3Importer.ThemeSettingsImporter: CPSSkins is not installed")
            LOG("CPS3Importer.ThemeSettingsImporter CPSSkins is not installed", ERROR,
                self.file_path)
            return

        self.log("Importing theme settings from file " + self.file_path)
        LOG("Importing theme settings from file", INFO, self.file_path)

        doc = ElementTree(file=self.file_path)
        root = doc.getroot()
        settings_els = xpath_findall(root, "{%s}field" % self.ns_uri)
        for setting_el in settings_els:
            self.buildField(container, setting_el)

    def buildField(self, container, field_el):
        """Build a theme setting field
        """

        field_id, field_value = self.getField(field_el)
        if field_value is not None:
            # set the field property value
            if getattr(aq_base(container), field_id, None) is not None:
                setattr(container, field_id,field_value)
        else:
            # treat more complex data structures
            # this may be rewritten in a more generic way.
            if field_id == 'externalthemes':
                externalthemes = []
                list_els = xpath_findall(field_el, "{%s}list" % self.ns_uri)
                for list_el in list_els:
                    map_els = xpath_findall(list_el, "{%s}map" % self.ns_uri)
                    for map_el in map_els:
                        externalthemes.append(self.getDictFields(map_el))
                if getattr(aq_base(container), field_id, None) is not None:
                    setattr(container, field_id, externalthemes)

            if field_id == 'method_themes':
                map_els = xpath_findall(field_el, "{%s}map" % self.ns_uri)
                if len(map_els) > 0:
                    method_themes = self.getDictFields(map_els[0])
                    if getattr(aq_base(container), field_id, None) is not None:
                        setattr(container, field_id, method_themes)

    def getDictFields(self, el):
        """Return a dictionary of field id:value"""
        els = xpath_findall(el, "{%s}field" % self.ns_uri)
        fields = {}
        for el in els:
            field_id, value = self.getField(el)
            if value is not None:
                fields[field_id] = value
        return fields

    def getField(self, el):
        field_id = el.get('id')
        value_text = el.get('value')
        if value_text is None:
            return field_id, None
        value = None
        field_type = el.get('type')
        if field_type == 'int':
            value = str(value_text)
        elif field_type == 'list':
            value = value_text.split(',')
        elif field_type == 'tuple':
            value = tuple(value_text.split(','))
        elif field_type == 'boolean':
            value = booleanParser(value_text)
        else:
            value = value_text
        return field_id, value


class GroupsImporter(IOBase):

    def __init__(self, portal, file_name, dir_name):
        self.portal = portal
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name,
                                      self.file_name)
        self.ns_uri = main_namespace_uri + 'cpsgroup#'

    def importFile(self):
        """Parse the XML file into an elementtree structure"""

        self.log('Importing groups from file ' + self.file_path)

        doc = ElementTree(file=self.file_path)
        root = doc.getroot()

        group_els = xpath_findall(root, '{%s}group' % self.ns_uri)

        #acl_users = self.portal.acl_users
        #for group_el in group_els:
        #    groupname = group_el.get('name')
        #    title = group_el.get('title')
        #    if acl_users.getGroupById(groupname, default=None) is None:
        #        acl_users.userFolderAddGroup(groupname, title)

        groups_dir = self.portal.portal_directories.groups
        for group_el in group_els:
            groupname = group_el.get('name')
            title = group_el.get('title')
            entry = {'group' : groupname,
                     'title' : title,
                     }
            groups_dir.createEntry(entry)


class MembersImporter(IOBase):

    def __init__(self, portal, file_name, dir_name):
        self.portal = portal
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name,
                                      self.file_name)
        self.ns_uri = main_namespace_uri + 'cpsmember#'

    def importFile(self):
        """Parse the XML file into an elementtree structure"""

        self.log('Importing members from file ' + self.file_path)

        member_ids = self.portal.portal_membership.listMemberIds()
        members_dir = self.portal.portal_directories.members
        mtool = self.portal.portal_membership

        doc = ElementTree(file=self.file_path)
        root = doc.getroot()

        members = xpath_findall(root, '{%s}member' % self.ns_uri)

        for member_el in members:
            userid = member_el.get('id')
            if userid in member_ids:
                continue

            password = member_el.get('password')
            sn = member_el.get('sn')
            given_name = member_el.get('givenName')
            email = member_el.get('email')
            homeless = int(member_el.get('homeless'))

            roles = []
            roles_el = xpath_findall(member_el, '{%s}roles' % self.ns_uri)
            if roles_el:
                roles_el = roles_el[0]
                role_els = xpath_findall(roles_el, '{%s}role' % self.ns_uri)
                for role_el in role_els:
                    roles.append(role_el.text)

            groups = []
            groups_el = xpath_findall(member_el, '{%s}groups' % self.ns_uri)
            if groups_el:
                groups_el = groups_el[0]
                group_els = xpath_findall(groups_el, '{%s}group' % self.ns_uri)
                for group_el in group_els:
                    groups.append(group_el.text)

            if not password:
                password = userid

            entry = {'id': userid,
                     'password': password,
                     'confirm': password,
                     'sn': sn,
                     'givenName': given_name,
                     'email': email,
                     'roles': roles,
                     'groups': groups,
                     'homeless': homeless,
                     }

            # handle possible additional elements
            el_names_to_exclude = ('{%s}groups' % self.ns_uri,
                                   '{%s}roles' % self.ns_uri)
            other_els = [el for el in xpath_findall(member_el, '*')
                         if el.tag not in el_names_to_exclude]

            for el in other_els:
                sub_elements = xpath_findall(el, '*')
                if sub_elements:
                    key = re.sub('{.*}', '', el.tag)
                    val = [sub_el.text for sub_el in sub_elements]
                    entry[key] = val
                else:
                    val = el.text
                    if val:
                        key = re.sub('{.*}', '', el.tag)
                        entry[key] = val

            # encode to iso-8859-15 all str values
            for key, val in entry.items():
                # we use 'basestring' because isinstance(val, str) leads
                # to 'ascii' codec can't encode character... as we may have
                # encoded values.
                if isinstance(val, basestring):
                    entry[key] = toLatin9(val)

            members_dir.createEntry(entry)

            # create home folders
            #member_id = entry['id']
            #if mtool.getHomeFolder(member_id) is None and not homeless:
            #    mtool.createMemberArea(member_id)


class SubscriptionsImporter(IOBase):

    def __init__(self, portal, file_name, dir_name):
        self.portal = portal
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name,
                                      self.file_name)
        self.ns_uri = main_namespace_uri + 'cpssubscription#'

    def importFile(self):
        """Parse the XML file into an elementtree structure"""

        self.log('Importing groups from file ' + self.file_path)

        doc = ElementTree(file=self.file_path)
        root = doc.getroot()

        subs_els = xpath_findall(root, '{%s}subscription' % self.ns_uri)

        subscriptions = []

        for el in subs_els:
            el_str = '{%s}events/{%s}event' % (self.ns_uri, self.ns_uri)
            event_els = xpath_findall(el, el_str)
            d = {'member_id': el.get('member_id'),
                 'member_email': el.get('member_email'),
                 'rpath': el.get('rpath'),
                 'events': [event_el.get('id') for event_el in event_els],
                 }
            subscriptions.append(d)

        items = [(len(sub['rpath']), sub) for sub in subscriptions]
        items.sort()
        subscriptions[:] = [t[1] for t in items]

        stool = getToolByName(self.portal, 'portal_subscriptions')
        utool = getToolByName(self.portal, 'portal_url')

        for sub in subscriptions:
            context = self.portal.restrictedTraverse(sub['rpath'], None)
            if context is not None:
                container = stool.getSubscriptionContainerFromContext(context)

                for event in sub['events']:
                    subscription = container.getSubscriptionById(event)
                    # We will use ExplicitRecipientsRule
                    exp_rule = subscription.getRecipientsRules()[0]

                    # Building member struct with compuslory information
                    context_relative_url = utool.getRelativeContentURL(context)
                    member_struct = {}
                    member_struct['id'] = sub['member_id']
                    member_struct['subscription_relative_url'] = [context_relative_url]

                    # Trying to subscribe the member
                    if not exp_rule.updateMembers(member_struct):
                        mid, me, mr = sub['member_id'], sub['member_email'], sub['rpath']
                        LOG('CPS3Importer: importFile', INFO,
                            'Error : Error subscribing %s to event %s under %s' % (mid, me, mr))

                if sub['rpath'].startswith('workspace'):
                    roles = ['Manager', 'WorkspaceMember',
                             'WorkspaceManager', 'WorkspaceReader']
                else:
                    roles = ['Manager', 'SectionManager',
                             'SectionReviewer', 'SectionReader']

                container.changePermissions(roles)
