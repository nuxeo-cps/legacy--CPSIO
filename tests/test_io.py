# (C) Copyright 2004-2005 Nuxeo SARL <http://nuxeo.com>
# Authors:
# Emmanuel Pietriga <ep@nuxeo.com>
# M.-A. Darche <madarche@nuxeo.com>
# Jean-Marc Orliaguet <jmo@ita.chalmers.se>
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

# TODO:
# - don't depend on getDocumentSchemas / getDocumentTypes but is there
#   an API for that ?

import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import unittest
from Testing import ZopeTestCase
import CPSIOTestCase

import shutil
from zipfile import ZipFile

from types import ListType, StringType, IntType, TupleType

from Products.CPSDocument.FlexibleTypeInformation import FlexibleTypeInformation
from Products.CPSCore.EventServiceTool import getEventService

from elementtree.ElementTree import ElementTree, Element, SubElement
from elementtree.ElementPath import findall as xpath_findall
from elementtree.ElementPath import find as xpath_find
from Products.CPSIO.export_modules.CPS3Exporter import Exporter as cps3exporter
from Products.CPSIO.import_modules.CPS3Importer import Importer as cps3importer
from Products.CPSIO.export_modules.CPS3Exporter import PortalTypeExporter as cps3ptexporter
from Products.CPSIO.import_modules.CPS3Importer import PortalTypeImporter as cps3ptimporter
from Products.CPSIO.export_modules.CPS3Exporter import SchemaExporter as cps3schexporter
from Products.CPSIO.import_modules.CPS3Importer import SchemaImporter as cps3schimporter
from Products.CPSIO.export_modules.CPS3Exporter import LayoutExporter as cps3layexporter
from Products.CPSIO.import_modules.CPS3Importer import LayoutImporter as cps3layimporter
from Products.CPSIO.export_modules.CPS3Exporter import VocabExporter as cps3vocexporter
from Products.CPSIO.import_modules.CPS3Importer import VocabImporter as cps3vocimporter
from Products.CPSIO.export_modules.CPS3Exporter import HierarchyExporter as cps3hrcexporter
from Products.CPSIO.import_modules.CPS3Importer import HierarchyImporter as cps3hrcimporter
from Products.CPSIO.export_modules.CPS3Exporter import WorkflowExporter as cps3wfexporter
from Products.CPSIO.import_modules.CPS3Importer import WorkflowImporter as cps3wfimporter
from Products.CPSIO.export_modules.CPS3Exporter import DocumentExporter as cps3docexporter
from Products.CPSIO.import_modules.CPS3Importer import DocumentImporter as cps3docimporter
from Products.CPSIO.import_modules.CPS3Importer import toLatin9

class TestIO(CPSIOTestCase.CPSIOTestCase):

    def afterSetUp(self):
        CPSIOTestCase.CPSIOTestCase.afterSetUp(self)
        os.makedirs(os.path.join(CLIENT_HOME, 'ut'))
        self.login('manager')
        self.io_tool = self.portal.portal_io

    def beforeTearDown(self):
        CPSIOTestCase.CPSIOTestCase.beforeTearDown(self)
        archive_file_path = os.path.join(CLIENT_HOME, 'ut.zip')
        if os.path.exists(archive_file_path):
            os.remove(archive_file_path)

        archive_import_file_path = os.path.join(INSTANCE_HOME, 'import', 'ut.zip')
        if os.path.exists(archive_import_file_path):
            os.remove(archive_import_file_path)

        archive_dir_path = os.path.join(CLIENT_HOME, 'ut')
        if os.path.exists(archive_dir_path):
            shutil.rmtree(archive_dir_path)

        self.logout()

    def test_cps3exporter(self):
        # instantiate main exporter
        exporter = cps3exporter(self.portal)

    def test_cps3ptexporter(self):
        # instantiate portal type exporter
        pt_exporter = cps3ptexporter(self.portal, 'ut')
        # export 2 portal types
        root = Element("{%s}portalTypes" % pt_exporter.ns_uri)
        pt_exporter.exportCPSFTI('Workspace', self.portal.portal_types.Workspace, root)
        pt_exporter.exportCPSFTI('Flexible', self.portal.portal_types.Flexible, root)
        doc = ElementTree(root)
        doc.write(pt_exporter.file_path)
        # import them back
        doc = ElementTree(file=pt_exporter.file_path)
        root = doc.getroot()
        # 2 pt should have been exported
        ftis = xpath_findall(root, "{%s}cpsfti" % pt_exporter.ns_uri)
        self.assertEquals(len(ftis), 2)
        for fti in ftis:
            # test some properties (represented as elements) existence and uniqueness
            for prop in ('title', 'description', 'schemas', 'layouts'):
                prop_elems = xpath_findall(fti, "{%s}%s" % (pt_exporter.ns_uri, prop))
                self.assertEquals(len(prop_elems), 1)
            # test some properties (represented as attributes) existence
            for prop in ('content_icon', 'cps_proxy_type', 'factory'):
                self.assert_(prop in fti.keys())

    def test_cps3schexporter(self):
        # instantiate schema exporter
        sch_exporter = cps3schexporter(self.portal, 'ut')
        # export 2 schemas
        root = Element("{%s}schemas" % sch_exporter.ns_uri)
        sch_exporter.exportSchema('metadata', self.portal.portal_schemas.metadata, root)
        sch_exporter.exportSchema('faqitem', self.portal.portal_schemas.faqitem, root)
        doc = ElementTree(root)
        doc.write(sch_exporter.file_path)
        # import them back
        doc = ElementTree(file=sch_exporter.file_path)
        root = doc.getroot()
        # 2 schemas should have been exported
        schemas = xpath_findall(root, "{%s}schema" % sch_exporter.ns_uri)
        self.assertEquals(len(schemas), 2)
        faqitem_schema = [schema for schema in
                          xpath_findall(root, "{%s}schema" % sch_exporter.ns_uri)
                          if schema.get('id') == 'faqitem'][0]
        self.assertEquals(len(xpath_findall(faqitem_schema,
                                            "{%s}field" % sch_exporter.ns_uri)),
                          3)

    def test_cps3layexporter(self):
        # instantiate layout exporter
        lay_exporter = cps3layexporter(self.portal, 'ut')
        # export 2 layouts
        root = Element("{%s}layouts" % lay_exporter.ns_uri)
        lay_exporter.exportLayout('metadata', self.portal.portal_layouts.metadata, root)
        lay_exporter.exportLayout('file', self.portal.portal_layouts.file, root)
        doc = ElementTree(root)
        doc.write(lay_exporter.file_path)
        # import them back
        doc = ElementTree(file=lay_exporter.file_path)
        root = doc.getroot()
        # 2 layouts should have been exported
        layouts = xpath_findall(root, "{%s}layout" % lay_exporter.ns_uri)
        self.assertEquals(len(layouts), 2)
        metadata_layout = [layout for layout in
                           xpath_findall(root, "{%s}layout" % lay_exporter.ns_uri)
                           if layout.get('id') == 'metadata'][0]
        self.assertEquals(len(xpath_findall(metadata_layout,
                                            "{%s}widgets" % lay_exporter.ns_uri)),
                          1)
        self.assertEquals(len(xpath_findall(metadata_layout,
                                            "{%s}rows" % lay_exporter.ns_uri)),
                          1)

    def XXXtest_cps3vocexporter(self):
        # instantiate vocab exporter
        voc_exporter = cps3vocexporter(self.portal, 'ut')
        # export 2 vocabularies
        root = Element("{%s}vocabularies" % voc_exporter.ns_uri)
        voc_exporter.exportCPSVocabulary('subject_voc', self.portal.portal_vocabularies.subject_voc, root)
        voc_exporter.exportDirectoryVocabulary('members', self.portal.portal_vocabularies.members, root)
        doc = ElementTree(root)
        doc.write(voc_exporter.file_path)
        # import them back
        doc = ElementTree(file=voc_exporter.file_path)
        root = doc.getroot()
        # 2 vocabularies should have been exported
        vocabularies = xpath_findall(root, "{%s}cpsVocabulary" % voc_exporter.ns_uri)
        self.assertEquals(len(vocabularies), 1)
        vocabularies = xpath_findall(root, "{%s}directoryVocabulary" % voc_exporter.ns_uri)
        self.assertEquals(len(vocabularies), 1)

    def test_cps3hrcexporter(self):
        # instantiate hierarchy exporter
        hrc_exporter = cps3hrcexporter(self.portal, 'ut', 0, 1, 0, 0)
        # export workspace and section roots
        root = Element("{%s}hierarchy" % hrc_exporter.ns_uri)
        portal_types_to_export = []
        for tree in self.portal.portal_trees.objectValues():
            for type in tree.getProperty('type_names'):
                if type not in portal_types_to_export:
                    portal_types_to_export.append(type)
        for object in self.portal.objectValues():
            if (object.meta_type == 'CPS Proxy Folder' and
                object.portal_type in portal_types_to_export):
                hrc_exporter.buildFolder(object, root)
        doc = ElementTree(root)
        doc.write(hrc_exporter.file_path)
        # import them back
        doc = ElementTree(file=hrc_exporter.file_path)
        root = doc.getroot()
        # 2 folders should have been exported
        folders = xpath_findall(root, "{%s}folder" % hrc_exporter.ns_uri)
        # sections, workspaces and members
        self.assertEquals(len(folders), 3)

    def test_cps3wfexporter(self):
        # instantiate wf exporter
        wf_exporter = cps3wfexporter(self.portal, 'ut')
        # export workspace_folder_wf, section_content_wf
        root = Element("{%s}workflows" % wf_exporter.ns_uri)
        el = SubElement(root, "{%s}workflowDefinitions" % wf_exporter.ns_uri)
        for wf_id, wf in [('workspace_folder_wf', self.portal.portal_workflow.workspace_folder_wf),
                          ('section_content_wf', self.portal.portal_workflow.section_content_wf)]:
            wf_exporter.buildWorkflow(wf_id, wf, el)
        doc = ElementTree(root)
        doc.write(wf_exporter.file_path)
        # import them back
        doc = ElementTree(file=wf_exporter.file_path)
        root = doc.getroot()
        # 2 workflows should have been exported
        workflows = xpath_findall(xpath_findall(root,
                                                "{%s}workflowDefinitions" % wf_exporter.ns_uri)[0],
                                  "{%s}workflow" % wf_exporter.ns_uri)
        self.assertEquals(len(workflows), 2)

    def test_cps3docexporter(self):
        # instantiate document exporter
        doc_exporter = cps3docexporter(self.portal, 'ut')
        # export documents located a workspace
        self.portal.portal_workflow.invokeFactoryFor(self.portal.workspaces,
                                                     'Flexible', 'flex_doc_47')
        self.portal.portal_workflow.invokeFactoryFor(self.portal.workspaces,
                                                     'FAQ', 'faq_doc_38')
        root = Element("{%s}documents" % doc_exporter.ns_uri)
        doc_exporter.buildRepository(root)
        doc = ElementTree(root)
        doc.write(doc_exporter.file_path)
        # import back
        doc = ElementTree(file=doc_exporter.file_path)
        root = doc.getroot()
        # 2 documents should have been exported
        documents = xpath_findall(root, "{%s}document" % doc_exporter.ns_uri)
        self.assertEquals(len(documents), 2)
        dataModels = xpath_findall(root,
                                   "{%s}document/{%s}dataModel" %
                                   (doc_exporter.ns_uri, doc_exporter.ns_uri))
        histories = xpath_findall(root,
                                  "{%s}document/{%s}history" %
                                  (doc_exporter.ns_uri, doc_exporter.ns_uri))
        proxies = xpath_findall(root,
                                "{%s}document/{%s}proxy" %
                                (doc_exporter.ns_uri, doc_exporter.ns_uri))

    def test_cps3importer(self):
        # instantiate main importer
        importer = cps3importer(self.portal)

    def test_cps3ptimporter(self):
        # instantiate portal type importer
        # nothing much to do ; actual comparison with
        # what has been exported is done in test_cps3ptimportexport
        pt_importer = cps3ptimporter(self.portal, 'portal_types', 'ut')

    def test_cps3schimporter(self):
        # instantiate schema importer
        # nothing much to do ; actual comparison with
        # what has been exported is done in test_cps3schimportexport
        sch_importer = cps3schimporter(self.portal, 'schemas', 'ut')

    def test_cps3layimporter(self):
        # instantiate layout importer
        # nothing much to do ; actual comparison with
        # what has been exported is done in test_cps3layimportexport
        lay_importer = cps3layimporter(self.portal, 'layouts', 'ut')

    def test_cps3vocimporter(self):
        # instantiate vocabulary importer
        # nothing much to do ; actual comparison with
        # what has been exported is done in test_cps3vocimportexport
        voc_importer = cps3vocimporter(self.portal, 'vocabularies', 'ut')

    def test_cps3hrcimporter(self):
        # instantiate hierarchy importer
        # nothing much to do ; actual comparison with
        # what has been exported is done in test_cps3hrcimportexport
        hrc_importer = cps3hrcimporter(self.portal, 'hierarchy', 'ut', 0, 1, 0, 0)

    def test_cps3wfimporter(self):
        # instantiate workflow importer
        # nothing much to do ; actual comparison with
        # what has been exported is done in test_cps3wfimportexport
        wf_importer = cps3wfimporter(self.portal, 'workflows', 'ut')

    def test_cps3docimporter(self):
        # instantiate document importer
        # nothing much to do ; actual comparison with
        # what has been exported is done in test_cps3docimportexport
        doc_importer = cps3docimporter(self.portal, 'documents', 'ut', 0)

    def test_cps3docimporter_buildProxy(self):
        # test robustness wrt missing revisions
        repotool = self.portal.portal_repository
        docid = repotool.getFreeDocid()
        ptype = 'News Item'
        repotool.constructContent(ptype, docid+ '__0002')
        # an overwriting importer
        imp = cps3docimporter(self.portal, 'documents', 'ut', 1)

        # proxy XML element
        proxy_el = Element('{%s}proxy' % imp.ns_uri)
        proxy_el.set('defaultLang', 'fr')
        proxy_el.set('docId', docid)
        lr_el = SubElement(proxy_el, "{%s}languageRevisions" % imp.ns_uri)
        lr_el.set('fr', '1')
        lr_el.set('en', '2')

        # buildProxy (calls getContent)
        rpath = 'workspaces/test_proxy'
        imp.buildProxy(proxy_el, rpath, ptype)

        # assertions
        proxy = self.portal.workspaces.test_proxy
        self.assertEquals(proxy.getLanguageRevisions(), {'en': 2})
        self.assertEquals(proxy.getDefaultLanguage(), 'en')

    def test_cps3ptimportexport(self):
        # remember portal types for comparison
        # when we import them back
        ttool = self.portal.portal_types
        old_types = {}
        for pt_id, pt in ttool.objectItems():
            if isinstance(pt, FlexibleTypeInformation):
                old_types[pt_id] = pt.propertyItems()
        # export types
        pt_exporter = cps3ptexporter(self.portal, 'ut')
        filen = pt_exporter.exportFile()
        ttool.manage_delObjects(ttool.objectIds())
        # import them back
        pt_importer = cps3ptimporter(self.portal, filen, 'ut')
        pt_importer.importFile()
        # compare types with older versions (previous to export)
        new_types = {}
        for pt_id, pt in ttool.objectItems():
            if isinstance(pt, FlexibleTypeInformation):
                new_types[pt_id] = pt.propertyItems()
        old_types_keys = old_types.keys()
        new_types_keys = new_types.keys()
        # actual comparison begins here
        self.assertEquals(len(old_types_keys), len(new_types_keys))
        # test that all types still exist
        for type_id in old_types_keys:
            self.assert_(type_id in new_types_keys)
        # for each type, test that properties exist and have the same
        # value for each type
        for type_id in old_types_keys:
            old_type_props = old_types.get(type_id)
            new_type_props = {}
            for prop in new_types.get(type_id):
                new_type_props[prop[0]] = prop[1]
            new_type_props_keys = new_type_props.keys()
            for old_prop in old_type_props:
                self.assert_(old_prop[0] in new_type_props_keys)
                if isinstance(old_prop[1], StringType) or isinstance(old_prop[1],IntType):
                    self.assertEquals(old_prop[1], new_type_props.get(old_prop[0]))
                elif isinstance(old_prop[1], ListType) or isinstance(old_prop[1],TupleType):
                    new_type_props_values = new_type_props.get(old_prop[0])
                    self.assertEquals(len(old_prop[1]), len(new_type_props_values))
                    for item in old_prop[1]:
                        self.assert_(item in new_type_props_values)

    def test_cps3schimportexport(self):
        # remember schemas for comparison
        # when we import them back
        stool = self.portal.portal_schemas
        old_schemas = {}
        for schema_id, schema in stool.objectItems():
            old_schemas[schema_id] = schema.items()
        # export schemas
        sch_exporter = cps3schexporter(self.portal, 'ut')
        filen = sch_exporter.exportFile()
        stool.manage_delObjects(stool.objectIds())
        # import them back
        sch_importer = cps3schimporter(self.portal, filen, 'ut')
        sch_importer.importFile()
        # compare schemas with older versions (previous to export)
        new_schemas = {}
        for schema_id, schema in stool.objectItems():
            new_schemas[schema_id] = schema.items()
        new_schema_keys = new_schemas.keys()
        for old_schema_id, old_schema in old_schemas.items():
            self.assert_(old_schema_id in new_schema_keys)
            new_schema = new_schemas[old_schema_id]
            new_schema_fields = {}
            for field in new_schema:
                new_schema_fields[field[0]] = field[1]
            new_schema_field_keys = new_schema_fields.keys()
            for old_field in old_schema:
                self.assert_(old_field[0] in new_schema_field_keys)
                new_field = new_schema_fields[old_field[0]]
                new_props = {}
                for new_prop_id, new_prop in new_field.propertyItems():
                    new_props[new_prop_id] = new_prop
                new_prop_keys = new_props.keys()
                for old_prop_id, old_prop_value in old_field[1].propertyItems():
                    self.assert_(old_prop_id in new_prop_keys)
                    if isinstance(old_prop_value, StringType) or isinstance(old_prop_value,IntType):
                        self.assertEquals(old_prop_value, new_props[old_prop_id])
                    elif isinstance(old_prop_value, ListType) or isinstance(old_prop_value, TupleType):
                        new_prop_value = new_props[old_prop_id]
                        for item in old_prop_value:
                            self.assert_(item in new_prop_value)

    def test_cps3layimportexport(self):
        # remember layouts for comparison
        # when we import them back
        ltool = self.portal.portal_layouts
        old_layouts = {}
        for layout_id, layout in ltool.objectItems():
            old_layouts[layout_id] = layout.items()
        # export layouts
        lay_exporter = cps3layexporter(self.portal, 'ut')
        filen = lay_exporter.exportFile()
        ltool.manage_delObjects(ltool.objectIds())
        # import them back
        lay_importer = cps3layimporter(self.portal, filen, 'ut')
        lay_importer.importFile()
        # compare layouts with older versions (previous to export)
        new_layouts = {}
        for layout_id, layout in ltool.objectItems():
            new_layouts[layout_id] = layout.items()
        new_layout_keys = new_layouts.keys()
        for old_layout_id, old_layout in old_layouts.items():
            self.assert_(old_layout_id in new_layout_keys)
            new_layout = new_layouts[old_layout_id]
            new_layout_widgets = {}
            for widget in new_layout:
                new_layout_widgets[widget[0]] = widget[1]
            new_layout_widget_keys = new_layout_widgets.keys()
            for old_widget in old_layout:
                self.assert_(old_widget[0] in new_layout_widget_keys)
                new_widget = new_layout_widgets[old_widget[0]]
                new_props = {}
                for new_prop_id, new_prop in new_widget.propertyItems():
                    new_props[new_prop_id] = new_prop
                new_prop_keys = new_props.keys()
                for old_prop_id, old_prop_value in old_widget[1].propertyItems():
                    self.assert_(old_prop_id in new_prop_keys)
                    if isinstance(old_prop_value, StringType) or isinstance(old_prop_value,IntType):
                        self.assertEquals(old_prop_value, new_props[old_prop_id])
                    elif isinstance(old_prop_value, ListType) or isinstance(old_prop_value, TupleType):
                        new_prop_value = new_props[old_prop_id]
                        for item in old_prop_value:
                            self.assert_(item in new_prop_value)

    def test_cps3vocimportexport(self):
        # remember vocabs for comparison
        # when we import them back
        vtool = self.portal.portal_vocabularies
        old_vocabs = {}
        for vocab_id, vocab in vtool.objectItems():
            old_vocabs[vocab_id] = vocab
        # export vocabs
        voc_exporter = cps3vocexporter(self.portal, 'ut')
        filen = voc_exporter.exportFile()
        vtool.manage_delObjects(vtool.objectIds())
        # import them back
        voc_importer = cps3vocimporter(self.portal, filen, 'ut')
        voc_importer.importFile()
        new_vocabs = {}
        for vocab_id, vocab in vtool.objectItems():
            new_vocabs[vocab_id] = vocab
        new_vocab_keys = new_vocabs.keys()
        for old_vocab_id, old_vocab in old_vocabs.items():
            self.assert_(old_vocab_id in new_vocab_keys)
            new_vocab = new_vocabs[old_vocab_id]
            # check vocab properties
            new_vocab_props = {}
            for prop_id, prop in new_vocab.propertyItems():
                new_vocab_props[prop_id] = prop
            new_vocab_prop_keys = new_vocab_props.keys()
            for old_prop_id, old_prop in old_vocab.propertyItems():
                self.assert_(old_prop_id in new_vocab_prop_keys)
                self.assertEquals(old_prop, new_vocab_props[old_prop_id])
            # check vocab items
            new_vocab_items = {}
            for key, label in new_vocab.items():
                new_vocab_items[key] = label
            new_vocab_item_keys = new_vocab_items.keys()
            for old_item_key, old_item_label in old_vocab.items():
                old_msgid = old_vocab.getMsgid(old_item_key)
                new_msgid = new_vocab.getMsgid(old_item_key)
                self.assert_(old_item_key in new_vocab_item_keys)
                self.assertEquals(old_msgid, new_msgid)
                self.assertEquals(old_item_label, toLatin9(new_vocab_items[old_item_key]))

    def getWorkspaces(self, workspace):
        subworkspaces = [object for object in workspace.objectValues()
                         if object.portal_type == 'Workspace']
        return (workspace, [self.getWorkspaces(sws) for sws in subworkspaces])

    def getSections(self, section):
        subsections = [object for object in section.objectValues()
                       if object.portal_type == 'Section']
        return (section, [self.getSections(scs) for scs in subsections])

    def checkFolders(self, old_folders, new_folders):
        new_folders_dict = {}
        for f in new_folders:
            new_folders_dict[f[0].id] = f
        for old_folder in old_folders:
            self.assert_(old_folder[0].id in new_folders_dict.keys())
            new_folder = new_folders_dict[old_folder[0].id]
            self.assertEquals(old_folder[0].Title(), new_folder[0].Title())
            self.assertEquals(old_folder[0].getContent().Description(),
                              new_folder[0].getContent().Description())
            if old_folder[1] and new_folder[1]:
                self.checkFolders(old_folder[1], new_folder[1])

    def test_cps3hrcimportexport(self):
        # create some workspaces and sections
        wtool = self.portal.portal_workflow
        etool = getEventService(self.portal)
        f_id = 'ws1'
        wtool.invokeFactoryFor(self.portal.workspaces, 'Workspace', f_id)
        kw = {'Title': 'title for ws1',
              'Description': 'test_desc',
              'Language': 'fr',
              'Source': 'test CPS'}
        folder = getattr(self.portal.workspaces, f_id)
        folder.getEditableContent().edit(proxy=folder, **kw)
        etool.notifyEvent('modify_object', folder, {})
        f_id = 'ws1.1'
        wtool.invokeFactoryFor(folder, 'Workspace', f_id)
        kw = {'Title': 'title for ws1.1',
              'Description': 'test_desc2',
              'Language': 'en',
              'Source': 'test CPS'}
        folder2 = getattr(folder, f_id)
        folder2.getEditableContent().edit(proxy=folder2, **kw)
        etool.notifyEvent('modify_object', folder2, {})
        f_id = 'sc1'
        wtool.invokeFactoryFor(self.portal.sections, 'Section', f_id)
        kw = {'Title': 'title for sc1',
              'Description': 'test_desc',
              'Language': 'fr',
              'Source': 'test CPS'}
        folder = getattr(self.portal.sections, f_id)
        folder.getEditableContent().edit(proxy=folder, **kw)
        etool.notifyEvent('modify_object', folder, {})
        f_id = 'sc1.1'
        wtool.invokeFactoryFor(folder, 'Section', f_id)
        kw = {'Title': 'title for sc1.1',
              'Description': 'test_desc2',
              'Language': 'en',
              'Source': 'test CPS'}
        folder2 = getattr(folder, f_id)
        folder2.getEditableContent().edit(proxy=folder2, **kw)
        etool.notifyEvent('modify_object', folder2, {})

        # remember hierarchy for comparison
        # when we import it back
        old_workspaces = self.getWorkspaces(self.portal.workspaces)
        old_sections = self.getSections(self.portal.sections)

        # also remember .cps_boxes_root
        has_boxes = hasattr(self.portal, '.cps_boxes_root')
        if has_boxes:
            old_boxes = getattr(self.portal, '.cps_boxes_root').objectValues()

        # export hierarchy
        hrc_exporter = cps3hrcexporter(self.portal, 'ut', 0, 1, 0, 0)
        filen = hrc_exporter.exportFile()

        # erase hierarchy
        self.portal.manage_delObjects(['workspaces', 'sections'])
        if has_boxes:
            self.portal.manage_delObjects(['.cps_boxes_root'])

        # import it back
        hrc_importer = cps3hrcimporter(self.portal, filen, 'ut', 0, 1, 0, 0)
        hrc_importer.importFile()
        new_workspaces = self.getWorkspaces(self.portal.workspaces)
        new_sections = self.getSections(self.portal.sections)

        # recursive comparison of workspaces/ and sections/
        self.checkFolders([old_workspaces], [new_workspaces])
        self.checkFolders([old_sections], [new_sections])

        # compare .cps_boxes_root
        if has_boxes:
            self.assert_('.cps_boxes_root' in self.portal.objectIds())
            new_boxes = {}
            for box_id, box in getattr(self.portal, '.cps_boxes_root').objectItems():
                new_boxes[box_id] = box
            new_box_keys = new_boxes.keys()
            for old_box in old_boxes:
                self.assert_(old_box.id in new_box_keys)
                new_box = new_boxes.get(old_box.id)
                new_props = {}
                for prop_id, prop in new_box.propertyItems():
                    new_props[prop_id] = prop
                new_prop_keys = new_props.keys()
                for old_prop_id, old_prop in old_box.propertyItems():
                    self.assert_(old_prop_id in new_prop_keys)
                    prop_type = type(old_prop).__name__
                    if prop_type == 'list' or prop_type == 'tuple':
                        new_prop = new_props[old_prop_id]
                        for item in old_prop:
                            self.assert_(item in new_prop)
                    else:
                        self.assertEquals(old_prop, new_props[old_prop_id])

    def test_cps3wfimportexport(self):
        # remember workflows for comparison
        # when we import them back
        wtool = self.portal.portal_workflow
        old_workflows = {}
        for workflow_id, workflow in wtool.objectItems():
            old_workflows[workflow_id] = workflow
        # export workflows
        wf_exporter = cps3wfexporter(self.portal, 'ut')
        filen = wf_exporter.exportFile()
        wtool.manage_delObjects(wtool.objectIds())
        # import them back
        wf_importer = cps3wfimporter(self.portal, filen, 'ut')
        wf_importer.importFile()
        new_workflows = {}
        for workflow_id, workflow in wtool.objectItems():
            new_workflows[workflow_id] = workflow
        new_wf_ids = new_workflows.keys()
        # compare old and new workflows
        for old_workflow_id, old_workflow in old_workflows.items():
            self.assert_(old_workflow_id in new_wf_ids)
            new_workflow = new_workflows.get(old_workflow_id)
            self.assertEquals(old_workflow.title, new_workflow.title)
            self.assertEquals(old_workflow.state_var, new_workflow.state_var)
            for permission in old_workflow.permissions:
                self.assert_(permission in new_workflow.permissions)
            # check states
            new_state_ids = new_workflow.states.objectIds()
            for old_state in old_workflow.states.objectValues():
                self.assert_(old_state.id in new_state_ids)
                new_state = getattr(new_workflow.states, old_state.id)
                self.assertEquals(old_state.title, new_state.title)
                self.assertEquals(old_state.description, new_state.description)
                self.assertEquals(old_state.transitions, new_state.transitions)
                self.assertEquals(old_state.permissions, new_state.permissions)
                self.assertEquals(old_state.var_values, new_state.var_values)
            # check transitions
            new_transition_ids = new_workflow.transitions.objectIds()
            for old_transition in old_workflow.transitions.objectValues():
                self.assert_(old_transition.id in new_transition_ids)
                new_transition = getattr(new_workflow.transitions, old_transition.id)
                self.assertEquals(old_transition.title, new_transition.title)
                self.assertEquals(old_transition.description, new_transition.description)
                self.assertEquals(old_transition.new_state_id, new_transition.new_state_id)
                self.assertEquals(old_transition.trigger_type, new_transition.trigger_type)
                self.assertEquals(old_transition.actbox_name, new_transition.actbox_name)
                self.assertEquals(old_transition.actbox_url, new_transition.actbox_url)
                self.assertEquals(old_transition.actbox_category, new_transition.actbox_category)
                self.assertEquals(old_transition.script_name, new_transition.script_name)
                self.assertEquals(old_transition.after_script_name, new_transition.after_script_name)
                self.assertEquals(old_transition.transition_behavior, new_transition.transition_behavior)
                self.assertEquals(old_transition.clone_allowed_transitions, new_transition.clone_allowed_transitions)
                self.assertEquals(old_transition.checkout_allowed_initial_transitions, new_transition.checkout_allowed_initial_transitions)
                self.assertEquals(old_transition.checkin_allowed_transitions, new_transition.checkin_allowed_transitions)
                old_guard = old_transition.getGuard()
                new_guard = new_transition.getGuard()
                self.assertEquals(old_guard.getPermissionsText(), new_guard.getPermissionsText())
                self.assertEquals(old_guard.getRolesText(), new_guard.getRolesText())
                self.assertEquals(old_guard.getExprText(), new_guard.getExprText())
            # check scripts
            new_script_ids = new_workflow.scripts.objectIds()
            for old_script in old_workflow.scripts.objectValues():
                self.assert_(old_script.id in new_script_ids)
                new_script = getattr(new_workflow.scripts, old_script.id)
                self.assertEquals(old_script.title, new_script.title)
                old_code = old_script.read()
                new_code = new_script.read()
                self.assertEquals(old_code, new_code)
                for pr in old_script._proxy_roles:
                    self.assert_(pr in new_script._proxy_roles)
                self.assertEquals(old_script._owner, new_script._owner)
            # check variables
            new_var_ids = new_workflow.variables.objectIds()
            for old_var in old_workflow.variables.objectValues():
                self.assert_(old_var.id in new_var_ids)
                new_var = getattr(new_workflow.variables, old_var.id)
                self.assertEquals(old_var.description, new_var.description)
                self.assertEquals(old_var.for_status, new_var.for_status)
                self.assertEquals(old_var.for_catalog, new_var.for_catalog)
                self.assertEquals(old_var.default_value, new_var.default_value)
                self.assertEquals(old_var.getDefaultExprText(), new_var.getDefaultExprText())
                self.assertEquals(old_var.update_always, new_var.update_always)
                old_guard = old_var.getInfoGuard()
                new_guard = new_var.getInfoGuard()
                self.assertEquals(old_guard.getPermissionsText(), new_guard.getPermissionsText())
                self.assertEquals(old_guard.getRolesText(), new_guard.getRolesText())
                self.assertEquals(old_guard.getExprText(), new_guard.getExprText())

    def getFoldersAndDocs(self, folder):
        content = folder.objectValues()
        # Remove things without a ti like SubscriptionContainer
        content = [object for object in content
                   if object.getTypeInfo() is not None]
        docs = [object for object in content
                if object.getTypeInfo().cps_proxy_type == 'document']
        subfolders = [object for object in content
                      if (object.getTypeInfo().cps_proxy_type == 'folder' and
                          object.id != '.cps_workflow_configuration')]
        subfolderishdocs = [object for object in content
                            if object.getTypeInfo().cps_proxy_type == 'folderishdocument']
        return (folder, [self.getFoldersAndDocs(sfd) for sfd in subfolders],
                [self.getFoldersAndDocs(sfd) for sfd in subfolderishdocs], docs)

    def getRepository(self):
        res = {}
        for doc_id, doc in self.portal.portal_repository.objectItems():
            res[doc_id] = (doc,
                           self.portal.portal_repository.getHistory(doc_id[:doc_id.find('_')]))
        return res

    def checkProxy(self, old_proxy, new_proxy):
        # check folder rpath
        self.assertEquals(self.portal.portal_url.getRelativeUrl(old_proxy[0]),
                          self.portal.portal_url.getRelativeUrl(new_proxy[0]))
        # call method on subfolders
        new_subfolders = {}
        for sfd in new_proxy[1]:
            new_subfolders[self.portal.portal_url.getRelativeUrl(sfd[0])] = sfd
        for sfd in old_proxy[1]:
            old_rpath = self.portal.portal_url.getRelativeUrl(sfd[0])
            self.assert_(old_rpath in new_subfolders.keys())
            self.checkProxy(sfd, new_subfolders[old_rpath])
        # call method on subfolders
        new_subfolders = {}
        for sfd in new_proxy[2]:
            new_subfolders[self.portal.portal_url.getRelativeUrl(sfd[0])] = sfd
        for sfd in old_proxy[2]:
            old_rpath = self.portal.portal_url.getRelativeUrl(sfd[0])
            self.assert_(old_rpath in new_subfolders.keys())
            self.checkProxy(sfd, new_subfolders[old_rpath])
        # check document proxies
        new_docs = {}
        for doc in new_proxy[3]:
            new_docs[self.portal.portal_url.getRelativeUrl(doc)] = doc
        for old_doc in old_proxy[3]:
            rpath = self.portal.portal_url.getRelativeUrl(old_doc)
            self.assert_(rpath in new_docs.keys())
            new_doc = new_docs[rpath]
            self.assertEquals(old_doc.getDocid(), new_doc.getDocid())
            self.assertEquals(old_doc.getDefaultLanguage(),
                              new_doc.getDefaultLanguage())
            self.assertEquals(old_doc.getLanguageRevisions(),
                              new_doc.getLanguageRevisions())
            self.assertEquals(old_doc.getFromLanguageRevisions(),
                              new_doc.getFromLanguageRevisions())

    def test_cps3docimportexport(self):
        wtool = self.portal.portal_workflow
        etool = getEventService(self.portal)
        # create a bunch of documents
        f_id = 'ws1'
        wtool.invokeFactoryFor(self.portal.workspaces, 'Workspace', f_id)
        kw = {'Title': 'title for ws1',
              'Description': 'test_desc',
              'Language': 'fr',
              'Source': 'test CPS'}
        folder = getattr(self.portal.workspaces, f_id)
        folder.getEditableContent().edit(proxy=folder, **kw)
        etool.notifyEvent('modify_object', folder, {})
        f_id = 'sc1'
        wtool.invokeFactoryFor(self.portal.sections, 'Section', f_id)
        kw = {'Title': 'title for sc1',
              'Description': 'test_desc',
              'Language': 'fr',
              'Source': 'test CPS'}
        folder = getattr(self.portal.sections, f_id)
        folder.getEditableContent().edit(proxy=folder, **kw)
        etool.notifyEvent('modify_object', folder, {})
        ws1 = self.portal.workspaces.ws1
        sc1 = self.portal.sections.sc1
        # Image document
        d_id = 'img1'
        wtool.invokeFactoryFor(ws1, 'Image', d_id)
        #XXX: we should add an OFS.Image here and do a byte
        #     comparison later on its value
        kw = {'Title': 'img1 title',
              'Description': 'desc img1',
              'Language': 'en',
              'Source': 'test CPS source'}
        doc = getattr(ws1, d_id)
        doc.getEditableContent().edit(proxy=doc, **kw)
        etool.notifyEvent('modify_object', doc, {})
        # Flexible document
        d_id = 'flex1'
        wtool.invokeFactoryFor(ws1, 'Flexible', d_id)
        kw = {'Title': 'flex1 title',
              'Description': 'desc flex1',
              'Language': 'fr'}
        doc = getattr(ws1, d_id)
        doc.getEditableContent().edit(proxy=doc, **kw)
        etool.notifyEvent('modify_object', doc, {})
        # Folderish document (FAQ)
        d_id = 'faq1'
        wtool.invokeFactoryFor(ws1, 'FAQ', d_id)
        kw = {'Title': 'FAQ title',
              'Description': 'desc flex1',
              'Language': 'fr'}
        doc = getattr(ws1, d_id)
        doc.getEditableContent().edit(proxy=doc, **kw)
        etool.notifyEvent('modify_object', doc, {})
        # document inside folderish document
        d_id = 'q1'
        wtool.invokeFactoryFor(doc, 'FAQitem', d_id)
        kw = {'Title': 'question title?',
              'Description': 'question answer',
              'Language': 'en'}
        doc2 = getattr(doc, d_id)
        doc2.getEditableContent().edit(proxy=doc2, **kw)
        etool.notifyEvent('modify_object', doc2, {})
        # submit/publish some of them
        d_id = 'flex1'
        doc = getattr(ws1, d_id)
        wtool.doActionFor(doc, 'copy_submit', comment='flex1 submit test',
                          dest_container='sections/sc1', initial_transition='submit')
        doc = getattr(sc1, d_id)
        wtool.doActionFor(doc, 'accept', comment='flex1 accept test')
        # remember everything for comparison after import
        old_workspace_proxies = self.getFoldersAndDocs(self.portal.workspaces)
        old_section_proxies = self.getFoldersAndDocs(self.portal.sections)
        old_repository = self.getRepository()
        # export documents
        doc_exporter = cps3docexporter(self.portal, 'ut')
        filen = doc_exporter.exportFile()
        # export hierarchy
        hrc_exporter = cps3hrcexporter(self.portal, 'ut', 0, 1, 0, 0)
        filen2 = hrc_exporter.exportFile()
        # erase hierarchy
        self.portal.workspaces.manage_delObjects(['ws1'])
        self.portal.sections.manage_delObjects(['sc1'])
        if (hasattr(self.portal.portal_repository, 'purgeDeletedRevisions') and
            hasattr(self.portal.portal_repository, 'purgeArchivedRevisions')):
            self.portal.portal_repository.purgeDeletedRevisions()
            self.portal.portal_repository.purgeArchivedRevisions(0)
        elif hasattr(self.portal.portal_repository, 'manage_purgeOrphans'):
            # cannot call manage_purgeOrphans direcly as REQUEST is mandatory
            infos = self.portal.portal_repository.getManagementInformation()
            self.portal.portal_repository.manage_delObjects(infos['unused'])
        # import hierarchy back
        hrc_importer = cps3hrcimporter(self.portal, filen2, 'ut', 0, 1, 0, 0)
        hrc_importer.importFile()
        # import documents back
        doc_importer = cps3docimporter(self.portal, filen, 'ut', 0)
        doc_importer.importFile()
        new_workspace_proxies = self.getFoldersAndDocs(self.portal.workspaces)
        new_section_proxies = self.getFoldersAndDocs(self.portal.sections)
        new_repository = self.getRepository()
        # begin actual comparison
        # check proxies (including workflow history)
        self.checkProxy(old_workspace_proxies, new_workspace_proxies)
        self.checkProxy(old_section_proxies, new_section_proxies)
        # check repository (including global workflow history)
        new_doc_ids = new_repository.keys()
        for old_doc_id, old_doc_and_hist in old_repository.items():
            old_doc = old_doc_and_hist[0]
            if old_doc.getTypeInfo().cps_proxy_type in ('document',
                                                        'folderishdocument'):
                # check only documents and folderish documents as folders
                # are created by HierarchyImporter using a different method
                # covered in earlier unit tests (besides, the doc_id changes
                # for them
                self.assert_(old_doc_id in new_doc_ids)
                new_doc = new_repository.get(old_doc_id)[0]
                # compare data models
                old_dm = old_doc.getTypeInfo().getDataModel(old_doc)
                new_dm = new_doc.getTypeInfo().getDataModel(new_doc)
                old_data = old_dm.data
                new_data = new_dm.data
                new_schemas = {}
                for schema in new_dm._schemas:
                    new_schemas[schema.id] = schema
                for old_schema in old_dm._schemas:
                    self.assert_(old_schema.id in new_schemas.keys())
                    new_schema = new_schemas[old_schema.id]
                    for old_field_id, old_field in old_schema.items():
                        self.assert_(old_field_id in new_schema.keys())
                        if old_field_id not in ('CreationDate', 'ModificationDate'):
                            # don't test these dates as they do change
                            new_field = new_schema.get(old_field_id)
                            old_value = old_data[old_field_id]
                            new_value = new_data[old_field_id]
                            self.assertEquals(old_value, new_value)
                # check workflow history
                old_history = old_doc_and_hist[1]
                new_history = new_repository.get(old_doc_id)[1]
                self.assertEquals(len(old_history), len(new_history))
                i = 0
                for old_event in old_history:
                    new_event = new_history[i]
                    i += 1
                    for key, val in old_event.items():
                        self.assert_(key in new_event.keys())
                        # do an str comparison as comparison for DateTime
                        # objects fails:
                        # AssertionError: DateTime('2004/07/02 09:52:23.771 GMT+2') != DateTime('2004/07/02 09:52:23.771 GMT+2')
                        self.assertEquals(str(val), str(new_event[key]))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestIO))
    return suite
