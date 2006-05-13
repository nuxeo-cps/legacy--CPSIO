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
from types import ListType, TupleType
from elementtree.ElementTree import ElementTree, Element, SubElement

from Acquisition import aq_base
from Globals import InitializeClass
from AccessControl.Permission import Permission
from AccessControl import ClassSecurityInfo
from zLOG import LOG, DEBUG, INFO, WARNING, ERROR
from DateTime.DateTime import DateTime

from Products.CMFCore.utils import getToolByName
try:
    from Products.CMFCore.permissions import ManagePortal
except ImportError: # CPS <= 3.2
    from Products.CMFCore.CMFCorePermissions import ManagePortal

from Products.CPSIO.BaseExporter import MAIN_NAMESPACE_URI, BaseExporter
from Products.CPSIO.IOBase import IOBase

SUBTRANSACTION_COMMIT = 10

class Exporter(BaseExporter):

    options_template = 'cps3exporter_form'
    options_table = [
        {'id': 'export_hierarchy',
         'depth': 0,
         'title': "Export Hierarchy",
         'label': 'cpsio_label_export_hierarchy',
         },
        {'id': 'export_hierarchy_save_local_roles',
         'depth': 1,
         'title': "Save local roles",
         'label': 'cpsio_label_save_local_roles',
         },
        {'id': 'export_hierarchy_save_boxes',
         'depth': 1,
         'title': "Save box configuration",
         'label': 'cpsio_label_save_boxes',
         },
        {'id': 'export_hierarchy_save_portlets',
         'depth': 1,
         'title': "Save portlet configuration",
         'label': 'cpsio_label_save_portlets',
         },
        {'id': 'export_hierarchy_save_local_themes',
         'depth': 1,
         'title': "Export local themes",
         'label': 'cpsio_label_save_local_themes',
         },
        {'id': 'export_documents',
         'depth': 0,
         'title': "Export documents",
         'label': 'cpsio_label_export_documents',
         },
        {'id': 'export_workflows',
         'depth': 0,
         'title': "Export workflows",
         'label': 'cpsio_label_export_workflows',
         },
        {'id': 'export_portal_types',
         'depth': 0,
         'title': "Export portal types",
         'label': 'cpsio_label_export_portal_types',
         },
        {'id': 'export_schemas',
         'depth': 0,
         'title': "Export schemas",
         'label': 'cpsio_label_export_schemas',
         },
        {'id': 'export_layouts',
         'depth': 0,
         'title': "Export layouts",
         'label': 'cpsio_label_export_layouts',
         },
        {'id': 'export_vocabularies',
         'depth': 0,
         'title': "Export vocabularies",
         'label': 'cpsio_label_export_vocabularies',
         },
        {'id': 'export_custom_skins',
         'depth': 0,
         'title': "Export custom skins",
         'label': 'cpsio_label_export_custom_skins',
         },
        {'id': 'export_theme_settings',
         'depth': 0,
         'title': "Export theme settings",
         'label': 'cpsio_label_export_theme_settings',
         },
        ]

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
        if 'export_schemas' in self.options:
            file_name = SchemaExporter(self.portal, self.dir_name).exportFile()
            el = SubElement(root, "{%s}cpsschemas" % self.ns_uri)
            el.set('ref', file_name)
        if 'export_layouts' in self.options:
            file_name = LayoutExporter(self.portal, self.dir_name).exportFile()
            el = SubElement(root, "{%s}cpslayouts" % self.ns_uri)
            el.set('ref', file_name)
        if 'export_vocabularies' in self.options:
            file_name = VocabExporter(self.portal, self.dir_name).exportFile()
            el = SubElement(root, "{%s}cpsvocabularies" % self.ns_uri)
            el.set('ref', file_name)
        if 'export_custom_skins' in self.options:
            file_name = SkinExporter(self.portal, self.dir_name).exportFile()
            el = SubElement(root, "{%s}cmfcustomskins" % self.ns_uri)
            el.set('ref', file_name)
        if 'export_workflows' in self.options:
            file_name = WorkflowExporter(self.portal, self.dir_name).exportFile()
            el = SubElement(root, "{%s}cpsworkflows" % self.ns_uri)
            el.set('ref', file_name)
        if ('export_hierarchy' in self.options or
            'export_documents' in self.options):
            slr = 'export_hierarchy_save_local_roles' in self.options
            sbx = 'export_hierarchy_save_boxes' in self.options
            spl = 'export_hierarchy_save_portlets' in self.options
            slt = 'export_hierarchy_save_local_themes' in self.options
            file_name = HierarchyExporter(self.portal, self.dir_name, slr, sbx, spl, slt).exportFile()
            el = SubElement(root, "{%s}cpshierarchy" % self.ns_uri)
            el.set('ref', file_name)
        if 'export_documents' in self.options:
            file_name = DocumentExporter(self.portal, self.dir_name).exportFile()
            el = SubElement(root, "{%s}cpsdocuments" % self.ns_uri)
            el.set('ref', file_name)
        if 'export_theme_settings' in self.options:
            file_name = ThemeSettingsExporter(self.portal, self.dir_name).exportFile()
            el = SubElement(root, "{%s}themesettings" % self.ns_uri)
            el.set('ref', file_name)

        doc = ElementTree(root)
        doc.write(self.file_path, encoding="iso-8859-15")

        self.archiveExport()

    def buildTree(self):
        root = Element("{%s}cpsdefinitions" % self.ns_uri)
        return root


InitializeClass(Exporter)

#
# CPS 3 Portal Type Exporter
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

        from Products.CPSDocument.FlexibleTypeInformation import\
             FlexibleTypeInformation

        for pt_id, pt in self.pt_tool.objectItems():
            # both Factory-based type info and cps flexible type info
            # are instances of Products.CMFCore.TypesTool.FactoryTypeInformation
            # but only the 2nd is instance of FlexibleTypeInformation
            if isinstance(pt, FlexibleTypeInformation):
                el = self.exportCPSFTI(pt_id, pt, root)
            else:
                el = self.exportCMFFTI(pt_id, pt, root)

        return root

    def exportCPSFTI(self, pt_id, fti, parent):
        """Build an elementtree representation of a CPS Flexible Type
        Information object"""

        #XXX: display_in_cmf_calendar, cps_workspace_wf and cps_section_wf
        #     are not exported as they are not present in the definition, but
        #     stored in other places (i.e. we have to deal with them in the
        #     appropriate place)

        el = SubElement(parent, "{%s}cpsfti" % self.ns_uri)
        el.set('id', pt_id)
        # process properties
        for prop in self._getFTIProperties(fti):
            # export some properties as attributes
            if prop[0] in ('content_icon', 'content_meta_type', 'product',
                           'factory', 'immediate_view', 'global_allow',
                           'filter_content_types', 'allow_discussion',
                           'cps_is_searchable', 'cps_proxy_type',
                           'cps_display_as_document_in_listing'):
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
                           'filter_content_types', 'allow_discussion',
                           'cps_is_searchable', 'cps_proxy_type',
                           'cps_display_as_document_in_listing',
                           'cps_is_portalbox'):
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
# CPS 3 Schema Exporter
#
class SchemaExporter(IOBase):

    def __init__(self, portal, dir_name):
        self.portal = portal
        self.sch_tool = self.portal.portal_schemas
        self.file_name = 'schemas'
        self.file_path = os.path.join(CLIENT_HOME, dir_name, self.file_name)
        self.ns_uri = MAIN_NAMESPACE_URI + 'cpsschemas#'

    def exportFile(self):
        """Export schemas"""

        self.log("Exporting schemas to file " + self.file_path)
        LOG("Exporting schemas to file", DEBUG, self.file_path)

        root = self.buildTree()
        doc = ElementTree(root)
        doc.write(self.file_path, encoding="iso-8859-15")
        return self.file_name

    def buildTree(self):
        """Build the elementtree representing all schemas"""

        root = Element("{%s}schemas" % self.ns_uri)

        for schema_id, schema in self.sch_tool.objectItems():
            self.exportSchema(schema_id, schema, root)

        return root

    def exportSchema(self, schema_id, schema, parent):
        """Build an elementtree representation of a CPS schema"""

        el = SubElement(parent, "{%s}schema" % self.ns_uri)
        el.set('id', schema_id)

        for field_id, field in schema.items():
            el2 = SubElement(el, "{%s}field" % self.ns_uri)
            el2.set('id', field_id)
            el2.set('field_type', field.meta_type)
            for field_prop_id, field_prop_value in field.propertyItems():
                if (field_prop_id != 'getFieldIdProperty' and
                    field_prop_value is not None and
                    field_prop_value != ''):
                    el3 = SubElement(el2, "{%s}%s" % (self.ns_uri, field_prop_id))
                    el3.text = str(field_prop_value)
                    el3.set('type', type(field_prop_value).__name__)

#
# CPS 3 Layout Exporter
#
class LayoutExporter(IOBase):

    def __init__(self, portal, dir_name):
        self.portal = portal
        self.ltool = self.portal.portal_layouts
        self.file_name = 'layouts'
        self.file_path = os.path.join(CLIENT_HOME, dir_name, self.file_name)
        self.ns_uri = MAIN_NAMESPACE_URI + 'cpslayouts#'

    def exportFile(self):
        """Export layouts"""

        self.log("Exporting layouts to file " + self.file_path)
        LOG("Exporting layouts to file", DEBUG, self.file_path)

        root = self.buildTree()
        doc = ElementTree(root)
        doc.write(self.file_path, encoding="iso-8859-15")
        return self.file_name

    def buildTree(self):
        """Build the elementtree representing all layouts"""

        root = Element("{%s}layouts" % self.ns_uri)

        for layout_id, layout in self.ltool.objectItems():
            self.exportLayout(layout_id, layout, root)

        return root

    def exportLayout(self, layout_id, layout, parent):
        """Build an elementtree representation of a CPS layout"""

        el = SubElement(parent, "{%s}layout" % self.ns_uri)
        el.set('id', layout_id)
        # get layout properties (should contain zpt prefix and allowed flexible widgets)
        for prop in layout.propertyItems():
            if prop[0] in ('style_prefix',):
                el.set(prop[0], prop[1])
            else:
                el2 = SubElement(el, "{%s}%s" % (self.ns_uri, prop[0]))
                el2.set('type', type(prop[1]).__name__)
                el2.text = str(prop[1])
        # get layout definition
        layout_def = layout.getLayoutDefinition()
        el.set('ncols', str(layout_def['ncols']))
        rows = layout_def['rows']
        el2 = SubElement(el, "{%s}rows" % self.ns_uri)
        for row in rows:
            el3 = SubElement(el2, "{%s}row" % self.ns_uri)
            for cell in row:
                el4 = SubElement(el3, "{%s}cell" % self.ns_uri)
                if cell['ncols'] != 1:
                    el4.set('ncols', str(cell['ncols']))
                el4.set('widget_id', cell['widget_id'])
        # get widgets
        el2 = SubElement(el, "{%s}widgets" % self.ns_uri)
        for widget in layout.items():
            el3 = SubElement(el2, "{%s}widget" % self.ns_uri)
            el3.set('id', widget[0])
            el3.set('widget_type', widget[1].meta_type)
            for widget_prop in widget[1].propertyItems():
                if widget_prop[0] in ('title', 'is_required', 'label',
                                      'label_edit', 'is_i18n', 'hidden_empty'):
                    el3.set(widget_prop[0], str(widget_prop[1]))
                elif widget_prop[1] is not None:
                    el4 = SubElement(el3, "{%s}%s" % (self.ns_uri, widget_prop[0]))
                    el4.text = str(widget_prop[1])
                    el4.set('type', type(widget_prop[1]).__name__)

#
# CPS 3 Vocabulary Exporter
#
class VocabExporter(IOBase):

    def __init__(self, portal, dir_name):
        self.portal = portal
        self.vtool = self.portal.portal_vocabularies
        self.file_name = 'vocabularies'
        self.file_path = os.path.join(CLIENT_HOME, dir_name, self.file_name)
        self.ns_uri = MAIN_NAMESPACE_URI + 'cpsvocabularies#'

    def exportFile(self):
        """Export vocabularies"""

        self.log("Exporting vocabularies to file " + self.file_path)
        LOG("Exporting vocabularies to file", DEBUG, self.file_path)

        root = self.buildTree()
        doc = ElementTree(root)
        doc.write(self.file_path, encoding="iso-8859-15")
        return self.file_name

    def buildTree(self):
        """Build the elementtree representing all vocabularies"""

        root = Element("{%s}vocabularies" % self.ns_uri)

        from Products.CPSSchemas.Vocabulary import CPSVocabulary
        method_vocab_present = 1
        dir_vocab_present = 1
        try:
            from Products.CPSSchemas.MethodVocabulary import MethodVocabulary
        except ImportError:
            method_vocab_present = 0
        try:
            from Products.CPSDirectory.DirectoryVocabulary import DirectoryVocabulary
        except ImportError:
            dir_vocab_present = 0

        for vocab_id, vocab in self.vtool.objectItems():
            if isinstance(vocab, CPSVocabulary):
                self.exportCPSVocabulary(vocab_id, vocab, root)
            elif method_vocab_present and isinstance(vocab, MethodVocabulary):
                self.exportMethodVocabulary(vocab_id, vocab, root)
            elif dir_vocab_present and isinstance(vocab, DirectoryVocabulary):
                self.exportDirectoryVocabulary(vocab_id, vocab, root)
            else:
                self.log("CPS3Exporter: VocabExporter: unsupported vocabulary type: %s" % vocab_id)
                LOG("CPS3Exporter: VocabExporter: unsupported vocabulary type: %s" % vocab_id, ERROR, vocab)
        return root

    def exportCPSVocabulary(self, vocab_id, vocab, parent):
        """Build an elementtree representation of a CPS Vocabulary"""

        el = SubElement(parent, "{%s}cpsVocabulary" % self.ns_uri)
        el.set('id', vocab_id)

        for prop_id, prop in vocab.propertyItems():
            if prop_id in ('title', 'title_msgid', 'acl_write_roles'):
                el.set(prop_id, str(prop))
            else:
                el2 = SubElement(el, "{%s}%s" % (self.ns_uri, prop_id))
                el2.text = str(prop)
        export_msgids = 0
        for key in vocab.keys():
            if vocab.getMsgid(key) is not None:
                export_msgids = 1
                break
        for item_key, item_label in vocab.items():
            el2 = SubElement(el, "{%s}item" % self.ns_uri)
            el2.set('key', item_key)
            msgid = vocab.getMsgid(item_key)
            if msgid is not None:
                el2.set('msgid', msgid)
            el2.text = item_label

    def exportDirectoryVocabulary(self, vocab_id, vocab, parent):
        """Build an elementtree representation of a CPS Directory Vocabulary

        Should also take care of CPS Directory Entry Vocabularies (subclass)"""

        dir_vocab_present = 1
        try:
            from Products.CPSDirectory.DirectoryVocabulary import DirectoryVocabulary
            from Products.CPSDirectory.DirectoryEntryVocabulary import DirectoryEntryVocabulary
        except ImportError:
            dir_vocab_present = 0

        if dir_vocab_present and isinstance(vocab, DirectoryEntryVocabulary):
            el = SubElement(parent, "{%s}directoryEntryVocabulary" % self.ns_uri)
        else:
            el = SubElement(parent, "{%s}directoryVocabulary" % self.ns_uri)
        el.set('id', vocab_id)

        for prop_id, prop in vocab.propertyItems():
            if prop_id in ('title', 'title_msgid', 'directory',
                           'add_empty_key', 'empty_key_pos'):
                el.set(prop_id, str(prop))
            else:
                el2 = SubElement(el, "{%s}%s" % (self.ns_uri, prop_id))
                el2.text = str(prop)
        # it makes no sense to export the vocabulary items since they are
        # computed dynamically from the directory's content

    def exportDirectoryEntryVocabulary(self, vocab_id, vocab, parent):
        """Build an elementtree representation of a CPS Directory Entry Vocabulary"""

        self.log("CPS3Exporter: VocabExporter: DirectoryEntryVocabulary not supported yet: %s will not be exported" % vocab_id)
        LOG("CPS3Exporter: VocabExporter: DirectoryEntryVocabulary not supported yet: %s will not be exported" % vocab_id, INFO, vocab)

    def exportMethodVocabulary(self, vocab_id, vocab, parent):
        """Build an elementtree representation of a CPS Method Vocabulary"""

        el = SubElement(parent, "{%s}methodVocabulary" % self.ns_uri)
        el.set('id', vocab_id)

        for prop_id, prop in vocab.propertyItems():
            if prop_id in ('title', 'title_msgid', 'get_vocabulary_method',
                           'add_empty_key', 'empty_key_pos'):
                el.set(prop_id, str(prop))
            else:
                el2 = SubElement(el, "{%s}%s" % (self.ns_uri, prop_id))
                el2.text = str(prop)
        # it makes no sense to export the vocabulary items since they are
        # computed dynamically from the method

#
# CMF custom skin Exporter
#
class SkinExporter(IOBase):

    def __init__(self, portal, dir_name):
        self.portal = portal
        self.repository = self.portal.portal_repository
        self.pttool = self.portal.portal_types
        self.utool = self.portal.portal_url
        self.pxtool = self.portal.portal_proxies
        self.dir_name = dir_name
        self.file_name = 'skins'
        self.file_path = os.path.join(CLIENT_HOME, dir_name, self.file_name)
        self.attachment_dir = self.file_name + '_files'
        self.attachment_dir_path = os.path.join(CLIENT_HOME, dir_name,
                                                self.attachment_dir)
        self.ns_uri = MAIN_NAMESPACE_URI + 'cmfskins#'

    def exportFile(self):
        """Export custom skins"""

        self.log("Exporting custom skins to file " + self.file_path)
        LOG("Exporting custom skins to file", DEBUG, self.file_path)

        # create dir for attachments and File-based objects (binary data)
        # (eager instantiation, might be empty)
        self.checkDirectory(os.path.join(CLIENT_HOME, self.dir_name,
                                         self.attachment_dir))
        # build XML document
        root = self.buildTree()
        doc = ElementTree(root)
        doc.write(self.file_path, encoding="iso-8859-15")
        return self.file_name

    def checkDirectory(self, path):
        """Check that directory exists (if not, create it)"""

        if not (os.path.exists(path) and os.path.isdir(path)):
            os.mkdir(path)

    def buildTree(self):
        """Build the elementtree representing custom skins"""

        root = Element("{%s}cmfskins" % self.ns_uri)

        self.buildSkins(root)
        return root

    def buildSkins(self, root_el):
        for item in self.portal.portal_skins.custom.objectValues():
            if item.meta_type == 'File':
                self.buildFile(root_el, item)
            elif item.meta_type == 'Page Template':
                self.buildPageTemplate(root_el, item)
            elif item.meta_type == 'DTML Method':
                self.buildDTMLMethod(root_el, item)
            else:
                self.log("SkinExporter: Error: object type %s not supported" % item.meta_type)
                LOG("SkinExporter: Error:", ERROR,
                    "object type %s not supported" % item.meta_type)

    def buildFile(self, parent, f):
        el = SubElement(parent, "{%s}file" % self.ns_uri)
        file_id = f.id()
        el.set('id', file_id)
        el.set('ref', "%s/%s" % (self.attachment_dir, file_id))
        el.set('content_type', f.content_type)
        el.set('title', f.title)
        f_path = os.path.join(self.attachment_dir_path, file_id)
        of = open(f_path, 'wb')
        of.write(str(f.data))
        of.flush()
        of.close()

    def buildPageTemplate(self, parent, f):
        el = SubElement(parent, "{%s}pageTemplate" % self.ns_uri)
        file_id = f.id
        file_name = file_id
        if not file_name.endswith('.pt'):
            file_name += '.pt'
        el.set('id', file_id)
        el.set('ref', "%s/%s" % (self.attachment_dir, file_name))
        el.set('content_type', f.content_type)
        el.set('title', f.title)
        f_path = os.path.join(self.attachment_dir_path, file_name)
        of = open(f_path, 'w')
        of.write(f.read())
        of.flush()
        of.close()

    def buildDTMLMethod(self, parent, f):
        el = SubElement(parent, "{%s}dtmlMethod" % self.ns_uri)
        file_id = f.name()
        file_name = file_id
        if not file_name.endswith('.dtml'):
            file_name += '.dtml'
        el.set('id', file_id)
        el.set('ref', "%s/%s" % (self.attachment_dir, file_name))
        el.set('title', f.title)
        f_path = os.path.join(self.attachment_dir_path, file_name)
        of = open(f_path, 'w')
        of.write(f.document_src())
        of.flush()
        of.close()

#
# CPS 3 Hierarchy Exporter
#
class HierarchyExporter(IOBase):

    #from  import CPSProxyFolder

    def __init__(self, portal, dir_name, save_local_roles, save_boxes, save_portlets, save_local_themes):
        self.portal = portal
        self.mtool = self.portal.portal_membership
        self.utool = self.portal.portal_url
        self.dir_name = dir_name
        self.file_name = 'hierarchy'
        self.file_path = os.path.join(CLIENT_HOME, dir_name, self.file_name)
        self.ns_uri = MAIN_NAMESPACE_URI + 'cpshierarchy#'
        self.save_local_roles = save_local_roles
        self.save_boxes = save_boxes
        self.save_portlets = save_portlets
        self.save_local_themes = save_local_themes
        # compute list of portal types that should be taken into account
        # (filtering on meta_type == 'CPS Proxy Folder' is not sufficient)
        # as objects like 'CPSForum' have this meta_type but are not considered
        # part of the hierarchy (or are they? maybe there should be an option)
        self.portal_types_to_export = []
        for tree in self.portal.portal_trees.objectValues():
            for type in tree.getProperty('type_names'):
                if type not in self.portal_types_to_export:
                    self.portal_types_to_export.append(type)

    def exportFile(self):
        """Export hierarchy"""

        self.log("Exporting hierarchy to file " + self.file_path)
        LOG("Exporting hierarchy to file", DEBUG, self.file_path)

        root = self.buildTree()
        doc = ElementTree(root)
        doc.write(self.file_path, encoding="iso-8859-15")
        return self.file_name

    def buildTree(self):
        """Build the elementtree representing hierarchy"""

        root = Element("{%s}hierarchy" % self.ns_uri)

        # get all CPS hierarchy elements which are direct children
        # of the portal object (typically sections/ and workspaces/)
        # and do a recursive descent of the tree
        for object in self.portal.objectValues():
            if (object.meta_type == 'CPS Proxy Folder' and
                object.portal_type in self.portal_types_to_export):
                # read note in __init__ for an explanation of this condition
                self.buildFolder(object, root)

        if self.save_boxes and hasattr(self.portal, '.cps_boxes_root'):
            self.buildBoxConfig(getattr(self.portal, '.cps_boxes_root'), root)

        # portlets
        if self.save_portlets:
            self.ptltool = getToolByName(self.portal, 'portal_cpsportlets', None)
            if self.ptltool is None:
                self.log("CPSPortlets is not installed. Portlets will not be exported")
                LOG("CPS3Exporter: CPSPortlets is not installed. Portlets will not be exported", INFO, self.file_path)
            else:
                self.buildPortletConfig(self.portal, root)

        return root

    def buildFolder(self, proxy_folder, parent):
        """Build an elementtree representation of a folder"""

        el = SubElement(parent, "{%s}folder" % self.ns_uri)
        # folder properties
        el.set('id', proxy_folder.id)
        pt = proxy_folder.portal_type
        el.set('portal_type', pt)
        folder = proxy_folder.getContent()
        el2 = SubElement(el, "{%s}properties" % self.ns_uri)
        for property_id, property in folder.propertyItems():
            if property:
                el3 = SubElement(el2, "{%s}%s" % (self.ns_uri, property_id))
                el3.text = str(property)
                el3.set('type', type(property).__name__)
        # folder datamodel
        el2 = SubElement(el, "{%s}datamodel" % self.ns_uri)
        dm = folder.getTypeInfo().getDataModel(folder)
        for key, val in dm.data.items():
            if type(val).__name__ != 'ImplicitAcquirerWrapper':
                # special field values like Image instances
                # are not supported yet
                el3 = SubElement(el2, "{%s}field" % self.ns_uri)
                el3.set('name', key)
                if val is None:
                    el3.set('type', 'None')
                else:
                    if isinstance(val, DateTime):
                        el3.set('type', DateTime.__name__)
                    else:
                        el3.set('type', type(val).__name__)
                    el3.text = str(val)
        # folder local roles
        if self.save_local_roles:
            self.buildLocalRoles(proxy_folder, el)

        # local boxes
        if self.save_boxes and hasattr(aq_base(proxy_folder), '.cps_boxes'):
            self.buildBoxConfig(getattr(aq_base(proxy_folder), '.cps_boxes'), el)

        # local portlets
        if self.save_portlets:
            self.ptltool = getToolByName(self.portal, 'portal_cpsportlets', None)
            if self.ptltool is not None:
                self.buildPortletConfig(proxy_folder, el)

        # local themes
        if self.save_local_themes:
            self.buildLocalThemeConfig(proxy_folder, el, '.cpsskins_theme')

        # local workflow config
        if hasattr(aq_base(proxy_folder), '.cps_workflow_configuration'):
            self.buildWFChainConfig(getattr(aq_base(proxy_folder), '.cps_workflow_configuration'), el)

        # process its children
        for object in proxy_folder.objectValues():
            if (object.meta_type == 'CPS Proxy Folder' and
                object.portal_type in self.portal_types_to_export):
                # read note in __init__ for an explanation of this condition
                self.buildFolder(object, el)

    def buildLocalRoles(self, proxy_folder, parent):
        """Build an elementtree representation of a folder's local roles"""

        # compute local roles
        dict_roles = self.mtool.getMergedLocalRolesWithPath(proxy_folder)
        rpath = self.utool.getRpath(proxy_folder)
        # Filter remove special roles
        local_roles_blocked = 0
        for user in dict_roles.keys():
            for item in dict_roles[user]:
                roles = item['roles']
                roles = [r for r in roles if r not in ('Owner', 'Member')]
                if user == 'group:role:Anonymous' and '-' in roles:
                    roles = [r for r in roles if r != '-']
                    if item['url'] == rpath:
                        local_roles_blocked = 1
                item['roles'] = roles

            dict_roles[user] = [x for x in dict_roles[user] if x['roles']]

            if not dict_roles[user]:
                del dict_roles[user]
        #find editable user with local roles defined in the context
        local_roles = []
        for user in dict_roles.keys():
            for item in dict_roles[user]:
                if item['url'] == rpath:
                    local_roles.append((user, item['roles']))
        # build elementtree
        if local_roles:
            el = SubElement(parent, "{%s}localRoles" % self.ns_uri)
            el.set('blocked_local_roles', str(local_roles_blocked))
            for lr in local_roles:
                if lr[1]:
                    el2 = SubElement(el, "{%s}usrRoles" % self.ns_uri)
                    el2.set('usrid', lr[0])
                    el2.set('roles', ','.join(lr[1]))

    def buildBoxConfig(self, box_container, parent):

        el = SubElement(parent, "{%s}boxes" % self.ns_uri)
        for box in box_container.objectValues():
            self.buildBox(box, el)

    def buildPortletConfig(self, folder, parent):
        ptltool = self.ptltool
        portlet_container = ptltool.getPortletContainer(context=folder, local=1)
        if portlet_container is not None:
            el = SubElement(parent, "{%s}portlets" % self.ns_uri)
            for portlet in portlet_container.listPortlets():
                if portlet is None:
                    continue
                self.buildPortlet(portlet, el, self.dir_name, self.ns_uri)

    def buildLocalThemeConfig(self, container, parent, propid):

        if container.hasProperty(propid):
            prop_value = container.getProperty(propid)
            prop_type = container.getPropertyType(propid)
            if prop_type == 'lines':
                prop_value = ','.join(prop_value)
            el = SubElement(parent, "{%s}localthemes" % self.ns_uri)
            el.set('type', prop_type)
            el.set('value', prop_value)

    def buildBox(self, box, parent):

        el = SubElement(parent, "{%s}box" % self.ns_uri)
        el.set('id', box.id)
        el.set('boxType', box.portal_type)
        for prop_id, prop in box.propertyItems():
            el2 = SubElement(el, "{%s}property" % self.ns_uri)
            el2.set('name', prop_id)
            el2.text = str(prop)
            el2.set('type', type(prop).__name__)
        # box guard
        guard = box.getGuard()
        if guard:
            g_permissions = guard.getPermissionsText()
            g_roles = guard.getRolesText()
            g_expression = guard.getExprText()
            if g_permissions or g_roles or g_expression:
                el2 = SubElement(el, "{%s}guard" % self.ns_uri)
                if g_permissions:
                    el2.set('permissions', g_permissions)
                if g_roles:
                    el2.set('roles', g_roles)
                if g_expression:
                    el2.set('expr', g_expression)

    def buildPortlet(self, portlet, parent, dir_name, ns_uri):

        portlet_id = portlet.id
        el = SubElement(parent, "{%s}portlet" % ns_uri)
        el.set('id', portlet_id)
        el.set('portletType', portlet.portal_type)
        # portlet guard
        guard = portlet.getGuard()
        if guard is not None:
            g_permissions = guard.getPermissionsText()
            g_roles = guard.getRolesText()
            g_groups = guard.getGroupsText()
            g_expression = guard.getExprText()
            if g_permissions or g_roles or g_expression:
                el2 = SubElement(el, "{%s}guard" % self.ns_uri)
                if g_permissions:
                    el2.set('permissions', g_permissions)
                if g_roles:
                    el2.set('roles', g_roles)
                if g_groups:
                    el2.set('groups', g_groups)
                if g_expression:
                    el2.set('expr', g_expression)
        # create a PortletExporter class instance
        portletexporter = PortletExporter(self.portal, dir_name, ns_uri)
        flex_schema = getattr(portlet, '.cps_schemas', None)
        if flex_schema is not None:
            portletexporter.buildFlexibleSchemas(el, flex_schema)
        flex_layout = getattr(portlet, '.cps_layouts', None)
        if flex_layout is not None:
            portletexporter.buildFlexibleLayouts(el, flex_layout)
        ti = portlet.getTypeInfo()
        portletexporter.buildDataModel(ti.getDataModel(portlet), el, portlet_id)
        return el

    def buildWFChainConfig(self, wf_config, parent):

        el = SubElement(parent, "{%s}workflow_chains" % self.ns_uri)
        for pt, wfs in wf_config._chains_by_type.items():
            el2 = SubElement(el, "{%s}chain" % self.ns_uri)
            el2.set('portal_type', pt)
            el2.set('value', ','.join(list(wfs)))
            el2.set('type', 'local')
        for pt, wfs in wf_config._chains_by_type_under.items():
            el2 = SubElement(el, "{%s}chain" % self.ns_uri)
            el2.set('portal_type', pt)
            el2.set('value', ','.join(list(wfs)))
            el2.set('type', 'below')

#
# CPS 3 Workflow Exporter
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
            chain = list(self.wtool.getGlobalChainFor(portal_type))
            if chain:
                el2 = SubElement(el, "{%s}globalChain" % self.ns_uri)
                el2.set('chain', ','.join(chain))
                el2.set('portal_type', portal_type)

        el = SubElement(root, "{%s}workflowDefinitions" % self.ns_uri)
        for wf_id, wf in self.wtool.objectItems():
            self.buildWorkflow(wf_id, wf, el)
        # provide transition_behavior mapping in case constant values change
        # in the code
        el = SubElement(root, "{%s}transitionBehaviors" % self.ns_uri)
        try:
            from Products.CPSWorkflow import workflow as CPSWorkflow
        except ImportError, e:
            if 'No module named CPSWorkflow' not in str(e):
                raise
            # BBB: for older CPS versions
            from Products.CPSCore import CPSWorkflow

        for transition_behavior in [attr for attr in CPSWorkflow.__dict__.keys()
                                    if attr.startswith('TRANSITION_')]:
            el2 = SubElement(el, "{%s}transitionBehavior" % self.ns_uri)
            el2.set('name', transition_behavior)
            el2.set('ref', str(getattr(CPSWorkflow, transition_behavior)))
        # provide trigger type mapping in case constant values change
        # in the code
        el = SubElement(root, "{%s}triggerTypes" % self.ns_uri)
        from Products.DCWorkflow import Transitions
        for trigger_type in [attr for attr in Transitions.__dict__.keys()
                             if attr.startswith('TRIGGER_')]:
            el2 = SubElement(el, "{%s}triggerType" % self.ns_uri)
            el2.set('name', trigger_type)
            el2.set('ref', str(getattr(Transitions, trigger_type)))
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
            el2.set('id', transition.getId())
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
            # CPS specific workflow transition data
            if transition.transition_behavior:
                tb = [str(i) for i in transition.transition_behavior]
                el2.set('transition_behavior', ','.join(tb))
            if transition.clone_allowed_transitions:
                el2.set('clone_allowed_transitions',
                        ','.join(list(transition.clone_allowed_transitions)))
            if transition.checkout_allowed_initial_transitions:
                el2.set('checkout_allowed_initial_transitions',
                        ','.join(list(transition.checkout_allowed_initial_transitions)))
            if transition.checkin_allowed_transitions:
                el2.set('checkin_allowed_transitions',
                        ','.join(list(transition.checkin_allowed_transitions)))

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
# CPS 3 Document Exporter
#
class DocumentExporter(IOBase):

    def __init__(self, portal, dir_name):
        self.portal = portal
        self.repository = self.portal.portal_repository
        self.pttool = self.portal.portal_types
        self.utool = self.portal.portal_url
        self.pxtool = self.portal.portal_proxies
        self.dir_name = dir_name
        self.file_name = 'documents'
        self.file_path = os.path.join(CLIENT_HOME, dir_name, self.file_name)
        self.attachment_dir = self.file_name + '_files'
        self.attachment_dir_path = os.path.join(CLIENT_HOME, dir_name,
                                                self.attachment_dir)
        self.ns_uri = MAIN_NAMESPACE_URI + 'cpsdocument#'
        # compute list of portal types that should not be taken into account
        # (filtering on meta_type == 'CPS Proxy Folder' is not sufficient)
        # as objects like 'CPSForum' have this meta_type but are not considered
        # part of the hierarchy
        self.portal_types_in_portal_tree = []
        for tree in self.portal.portal_trees.objectValues():
            for type in tree.getProperty('type_names'):
                if type not in self.portal_types_in_portal_tree:
                    self.portal_types_in_portal_tree.append(type)
        # Check if CPSForum is installed
        self.map_docs_to_comments = False
        dtool = getToolByName(self.portal, 'portal_discussion', None)
        if dtool is not None and dtool.meta_type == 'CPS Discussion Tool':
            self.map_docs_to_comments = True

    def exportFile(self):
        """Export documents"""

        self.log("Exporting documents to file " + self.file_path)
        LOG("Exporting documents to file", DEBUG, self.file_path)

        # create dir for attachments and File-based objects (binary data)
        # (eager instantiation, might be empty)
        self.checkDirectory(os.path.join(CLIENT_HOME, self.dir_name,
                                         self.attachment_dir))
        # build XML document
        root = self.buildTree()
        doc = ElementTree(root)
        doc.write(self.file_path, encoding="iso-8859-15")
        return self.file_name

    def buildTree(self):
        """Build the elementtree representing document proxies
        and document repository"""

        root = Element("{%s}documents" % self.ns_uri)
        # repository
        self.buildRepository(root)
        return root

    def buildRepository(self, parent):
        """Build the elementtree representing the document repository"""

        # documents

        docs = self.repository.objectItems()
        nb_docs = len(docs)
        i = 0
        for doc_id, doc in docs:
            i += 1
            if i == 1 or i % 20 == 0:
                if i + 20 > nb_docs:
                    j = nb_docs
                else:
                    j = i + 20
                self.log("CPS3 DocumentExporter: Processing documents [%s-%s] of %s" % (str(i), str(j), str(nb_docs)))
                LOG("CPS3 DocumentExporter", INFO,
                    "Processing documents [%s-%s] of %s" % (str(i), str(j), str(nb_docs)))
            type_info = doc.getTypeInfo()
            if type_info is not None:
                eligible_pt = type_info.cps_proxy_type in ('document', 'folderishdocument') or \
                              (type_info.cps_proxy_type == 'folder' and \
                               type_info.id not in self.portal_types_in_portal_tree)
            else:
                eligible_pt = 0
            if eligible_pt:
                LOG('CPS3 DocumentExporter:', DEBUG,
                    'Processing repository document %s' % doc_id)
                doc_el = self.buildRepositoryDocument(doc_id, doc, parent)
                LOG('CPS3 DocumentExporter:', DEBUG,
                    'Processed repository document %s' % doc_id)
                # make subtransaction every SUBTRANSACTION_COMMIT object
                # to free memory.
                if i % SUBTRANSACTION_COMMIT == 0:
                    get_transaction().commit(1)
                LOG('CPS3 DocumentExporter:', DEBUG,
                    'Subtransaction commit - %dth element' % i)
                # for each doc build its global status history
                self.buildDocumentStatusHistory(doc_id, doc_el)
                # and all associated proxies
                self.buildProxies(doc_id, doc_el)
        # XXX: permissions? should not be necessary as they should be computed
        #      from permissions set on associated proxies

    def buildRepositoryDocument(self, doc_id, doc, parent):
        """Build the elementtree representing a document in the repository"""

        el = SubElement(parent, "{%s}document" % self.ns_uri)
        el.set('id', doc_id)
        el.set('portalType', doc.getPortalTypeName())
        if doc.meta_type == 'CPS Document':
            flex_schema = getattr(doc, '.cps_schemas', None)
            if flex_schema is not None:
                self.buildFlexibleSchemas(el, flex_schema)
            flex_layout = getattr(doc, '.cps_layouts', None)
            if flex_layout is not None:
                self.buildFlexibleLayouts(el, flex_layout)
            self.buildDataModel(doc.getTypeInfo().getDataModel(doc), el, doc_id)
        elif doc.meta_type == 'CPSForum':
            self.buildDataModel(doc.getTypeInfo().getDataModel(doc), el, doc_id)
        elif doc.meta_type == 'Collector Document':
            self.buildDataModel(doc.getTypeInfo().getDataModel(doc), el, doc_id)
        #XXX: how should other objects be handled? We don't have anything
        #     else in the repository for now AFAIK, but we might one day
        else:
            self.log("DocumentExporter: unknown document type (ignored) " + doc.meta_type)
            LOG('DocumentExporter: unknown document type (ignored)', DEBUG, doc.meta_type)
        return el

    def buildFlexibleSchemas(self, parent, schema_container):

        el = SubElement(parent, "{%s}flexibleSchemas" % self.ns_uri)
        fake_sch_exporter = SchemaExporter(self.portal, '')
        for schema_id, schema in schema_container.objectItems():
            SchemaExporter.exportSchema(fake_sch_exporter, schema_id, schema, el)

    def buildFlexibleLayouts(self, parent, layout_container):

        el = SubElement(parent, "{%s}flexibleLayouts" % self.ns_uri)
        fake_layout_exporter = LayoutExporter(self.portal, '')
        for layout_id, layout in layout_container.objectItems():
            LayoutExporter.exportLayout(fake_layout_exporter, layout_id, layout, el)

    def buildDataModel(self, dm, parent, doc_id):
        """Build the elementtree representation of a CPSDocument datamodel"""

        el = SubElement(parent, "{%s}dataModel" % self.ns_uri)
        data = dm.data
        for schema in dm._schemas:
            for field_id, field in schema.items():
                if not (field_id.startswith('file_') or field_id.startswith('attachedFile_')):
                    # do not export fields starting with 'file_'
                    # as they contain text version of the actual data
                    # (for indexing)
                    #XXX: this is definitely not clean ; we need to compare
                    #     the field's id end with suffix_??? defined for the
                    #     associated schema field
                    el2 = SubElement(el, "{%s}field" % self.ns_uri)
                    el2.set('id', field_id)
                    value = data[field_id]
                    if value and type(value).__name__ == 'ImplicitAcquirerWrapper':
                        meta_type = getattr(value, 'meta_type', '')
                        el2.set('type', meta_type)
                        if meta_type == 'File' or meta_type == 'Image':
                            path = self.exportAttachedFile(value, doc_id)
                            el2.set('ref', path)
                            content_type = getattr(value, 'content_type', None)
                            if content_type:
                                el2.set('contentType', content_type)
                            el2.set('file_name', value.getId())
                            el2.set('title', value.title)
                        else:
                            path = self.exportAttachment(value, doc_id)
                            el2.set('file_name', value.getId())
                            el2.set('ref', path)
                    elif isinstance(value, DateTime):
                        el2.set('type', DateTime.__name__)
                        el2.text = str(value)
                    elif value is not None and value != 'None':
                        el2.set('type', type(value).__name__)
                        el2.text = str(value)
                    else:
                        el2.set('type', 'None')

    def buildDocumentStatusHistory(self, doc_id, parent):
        """Build the elementtree representation of a repository document's status history"""

        el = SubElement(parent, "{%s}history" % self.ns_uri)
        history = self.repository.getHistory(doc_id[:doc_id.find('_')])
        if history:
            for workflowEvent in history:
                el2 = SubElement(el, "{%s}workflowEvent" % self.ns_uri)
                for key, val in workflowEvent.items():
                    if key in ('dest_container', 'workflow_id', 'actor', 'time',
                               'action', 'review_state', 'time_str', 'state',
                               'rpath'):
                        el2.set(key, str(val))
                    elif key == 'language_revs':
                        el3 = SubElement(el2, "{%s}language_revs" % (self.ns_uri))
                        for lang, rev in val.items():
                            el3.set(lang, str(rev))
                    else:
                        el3 = SubElement(el2, "{%s}%s" % (self.ns_uri, key))
                        el3.text = str(val)
                        el3.set('type', type(val).__name__)

    def buildProxies(self, doc_id, parent):
        """Build the elementtree representing document proxies of a given folder"""

        true_doc_id = doc_id[:doc_id.find('_')]
        try:
            proxy_infos = self.pxtool.getProxyInfosFromDocid(true_doc_id)
        except KeyError, err:
            self.log("CPS3Exporter: No proxy for document id %s could be found. This is probably due to orphan versions left in the repository" % err)
            LOG('CPS3Exporter: DocumentExporter.buildProxies', WARNING,
                'No proxy for document id %s could be found. This is probably due to orphan versions left in the repository' % err)
            proxy_infos = []
        for proxy_info in proxy_infos:
            proxy = proxy_info['object']
            el = SubElement(parent, "{%s}proxy" % self.ns_uri)
            # rpath
            rpath = self.utool.getRelativeUrl(proxy)
            el.set('rpath', rpath)
            # associate commenting forum (if any) to document
            if self.map_docs_to_comments:
                self.setCommentForum(el, rpath)
            # properties
            # PropDocid
            el.set('docId', proxy.getDocid())
            # ProDefaultLanguage
            el.set('defaultLang', proxy.getDefaultLanguage())
            # PropLanguageRevisions
            lr = proxy.getLanguageRevisions()
            if lr:
                el2 = SubElement(el, "{%s}languageRevisions" % self.ns_uri)
                for lang, rev in lr.items():
                    el2.set(lang, str(rev))
            # PropFromLanguageRevisions
            flr = proxy.getFromLanguageRevisions()
            if flr:
                el2 = SubElement(el, "{%s}fromLanguageRevisions" % self.ns_uri)
                for lang, rev in flr.items():
                    el2.set(lang, str(rev))
            # Permissions
            not_acquired_permissions = []
            acquired_permissions = []
            # export not acquired permissions, or permissions
            # that are acquired but also define new roles locally
            for p in proxy.ac_inherited_permissions(1):
                name, value = p[:2]
                p = Permission(name, value, proxy)
                roles = p.getRoles(default=[])
                if not type(roles) is ListType:
                    not_acquired_permissions.append(name)
                else:
                    acquired_permissions.append(name)
            permissions = []
            for permission_name in not_acquired_permissions:
                mapping = [rop['name'] for rop in proxy.rolesOfPermission(permission_name)
                           if rop['selected'] == 'SELECTED']
                permissions.append((permission_name, mapping, 0))

            for permission_name in acquired_permissions:
                mapping = [rop['name'] for rop in proxy.rolesOfPermission(permission_name)
                           if rop['selected'] == 'SELECTED']
                if mapping and mapping != ['Manager']:
                    permissions.append((permission_name, mapping, 1))
            if permissions:
                el2 = SubElement(el, "{%s}permissions" % self.ns_uri)
                for permission in permissions:
                    el3 = SubElement(el2, "{%s}permission" % self.ns_uri)
                    el3.set('name', permission[0])
                    el3.set('roles', ','.join(permission[1]))
                    el3.set('acquired', str(permission[2]))

    def exportAttachedFile(self, value, doc_id):
        """Export File or Image object as a binary file"""

        file_id = value.id()
        dir_path = os.path.join(self.attachment_dir_path, doc_id)
        self.checkDirectory(dir_path)
        f_path = os.path.join(dir_path, file_id)
        f = open(f_path, 'wb')
        f.write(str(value.data))
        f.flush()
        f.close()
        return "%s/%s/%s" % (self.attachment_dir, doc_id, file_id)

    def exportAttachment(self, value, doc_id):
        """Export other kinds of attachments

        Difference with exportAttachedFile consist in how file name and data
        is retrieved from object
        """
        # XXX: Not sure we will ever go through this method - for robustness
        file_id = 'file__' + str(random.randrange(1, 10000, 1))
        dir_path = os.path.join(self.attachment_dir_path, doc_id)
        self.checkDirectory(dir_path)
        f_path = os.path.join(dir_path, file_id)
        f = open(f_path, mode='wb')
        f.write(str(value))
        f.flush()
        f.close()
        return "%s/%s/%s" % (self.attachment_dir, doc_id, file_id)

    def checkDirectory(self, path):
        """Check that directory exists (if not, create it)"""

        if not (os.path.exists(path) and os.path.isdir(path)):
            os.mkdir(path)

    def setCommentForum(self, proxy_el, rpath):
        """Associate proxy with forum used to comment document"""

        relative_url = self.portal.id + '/' + rpath
        comment_forum_url = self.portal.portal_discussion.getCommentForumURL(relative_url)
        if comment_forum_url:
            proxy_el.set('commentForum', comment_forum_url[len(self.portal.id)+1:])

#
# CPS 3 Portlet Exporter
#
class PortletExporter(IOBase, DocumentExporter):

    def __init__(self, portal, dir_name, ns_uri):
        self.portal = portal
        self.dir_name = dir_name
        self.file_name = 'portlets'
        self.file_path = os.path.join(CLIENT_HOME, dir_name, self.file_name)
        self.attachment_dir = self.file_name + '_files'
        self.attachment_dir_path = os.path.join(CLIENT_HOME, dir_name,
                                                self.attachment_dir)
        self.ns_uri = ns_uri
        self.checkDirectory(self.attachment_dir_path)

# CPSSkins Theme Settings Exporter
#
class ThemeSettingsExporter(IOBase):

    def __init__(self, portal, dir_name):
        self.portal = portal
        self.tmtool = getToolByName(self.portal, 'portal_themes', None)
        self.file_name = 'themesettings'
        self.file_path = os.path.join(CLIENT_HOME, dir_name, self.file_name)
        self.ns_uri = MAIN_NAMESPACE_URI + 'themesettings#'

    def exportFile(self):
        """Export theme settings"""

        if self.tmtool is None:
            self.log("CPS3Exporter.ThemeSettingsExporter: CPSSkins is not installed, theme settings will not be exported")
            LOG("CPS3Exporter.ThemeSettingsExporter: CPSSkins is not installed, theme settings will not be exported", INFO, self.file_path)
        else:
            self.log("Exporting theme settings to file " + self.file_path)
            LOG("Exporting theme settings to file", DEBUG, self.file_path)

            root = self.buildTree()
            doc = ElementTree(root)
            doc.write(self.file_path, encoding="iso-8859-15")
        return self.file_name

    def buildTree(self):
        """Build the elementtree representing theme settings"""

        root = Element("{%s}themesettings" % self.ns_uri)
        for field_id in ('accesskey',
                         'debug_mode',
                         'externalthemes',
                         'method_themes'):
            value = getattr(aq_base(self.tmtool), field_id, None)
            if value is None:
                continue
            self.buildField(field_id, value, root)
        return root

    def buildField(self, field_id, field, parent):
        if field_id:
            el = SubElement(parent, "{%s}field" % self.ns_uri)
            el.set('id', field_id)
        else:
            el = parent
        field_type = type(field).__name__
        if field_type in ('PersistentList', 'list'):
            self.buildList(field, el)
        elif field_type in ('PersistentMapping', 'dict'):
            self.buildDict(field, el)
        else:
            value = str(field)
            el.set('type', field_type)
            el.set('value', value)

    def buildDict(self, field, parent):
        el = SubElement(parent, "{%s}map" % self.ns_uri)
        for k, v in field.items():
            self.buildField(k, v, el)

    def buildList(self, field, parent):
        el = SubElement(parent, "{%s}list" % self.ns_uri)
        for l in field:
            self.buildField('', l, el)
