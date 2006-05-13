# (C) Copyright 2004 Nuxeo SARL <http://nuxeo.com>
# (c) Copyright 2004 Chalmers University of Technology <http://www.chalmers.se>
# Authors: Jean-Marc Orliaguet
# Original author: Emmanuel Pietriga <ep@nuxeo.com>
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

import os

from OFS.Image import Image
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from zLOG import LOG, DEBUG, INFO, ERROR, WARNING

from Products.CMFCore.utils import getToolByName
from Products.CPSIO.BaseImporter import BaseImporter
from Products.CPSIO.IOBase import IOBase
from Products.CPSIO.import_modules.CPS3Importer import PortletImporter

from elementtree.ElementTree import ElementTree
from elementtree.ElementPath import findall as xpath_findall
from elementtree.ElementPath import find as xpath_find

main_namespace_uri = 'http://www.nuxeo.com/2004/06/'
# adding 2 for surrounding curly braces {} of James Clark's NS syntax
# http://www.jclark.com/xml/xmlns.htm
main_namespace_uri_len = len(main_namespace_uri) + 2

def toLatin9(s):
    if s is None:
        return None
    else:
        return s.encode('iso-8859-15', 'ignore')

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

def integerParser(literalValue, defaultValue=0):
    try:
        res = int(literalValue)
        return res
    except ValueError:
        return defaultValue

def listParser(literalValue, defaultValue=[]):
    res = literalValue.split(',')
    if res != ['']:
        return res
    return defaultValue

class Importer(BaseImporter):

    options_template = 'cpsskinsimporter_form'
    options_table = [
        {'id': 'import_overwrite',
         'depth': 1,
         'title': "Overwrite existing theme objects in case of conflict",
         'label': 'cpsio_label_cpsskins_overwrite',
         },
        ]

    security = ClassSecurityInfo()
    security.declareObjectPublic()

    __roles__=None
    __allow_access_to_unprotected_subobjects__=1

    def __init__(self, portal):
        self.portal = portal
        self.ns_uri = main_namespace_uri + 'cpsskins#'

    def buildObject(self, el):
        """Build a schema definition"""

        schema_def = {}
        schema_def['id'] = el.get('id')
        schema_def['type'] = el.get('type')
        prop_els = xpath_findall(el, "{%s}field" % self.ns_uri)
        for prop_el in prop_els:
            prop_id = prop_el.get('name')
            prop_value = prop_el.get('value')
            prop_type = prop_el.get('type')
            # post-processing
            if prop_type == 'boolean':
                prop_value = booleanParser(prop_value)
            elif prop_type == 'int':
                prop_value = integerParser(prop_value)
            elif prop_type in ('multiple selection', 'lines'):
                prop_value = listParser(prop_value)
            else:
                prop_value = toLatin9(prop_value)
            schema_def[prop_id] = prop_value
        return schema_def

    def createObject(self, container, object_def):
        """Add layout items"""

        id = object_def['id']

        # create the item
        type_name = object_def['type']
        del object_def['type']
        del object_def['id']
        container.invokeFactory(type_name, id, **object_def)
        obj = getattr(container.aq_inner.aq_explicit, id, None)

        # return the created item
        return obj

    def importFile(self):
        """Main import"""

        self.log("Importing file " + self.file_path)
        LOG("Importing file", INFO, self.file_path)
        doc = ElementTree(file=self.file_path)
        root = doc.getroot()

        options = self.options
        overwrite = 'import_overwrite' in self.options

        ThemeImporter(self.portal, self.dir_name).updateTheme(root, overwrite)

    def getRef(self, ns_uri, elem_name, el):
        els = xpath_findall(el, "{%s}%s" % (ns_uri, elem_name))
        if len(els) > 0:
            return els[0].get('ref')
        else:
            return None

InitializeClass(Importer)

#
# CPSSkins Theme Importer
#
class ThemeImporter(IOBase, Importer):

    def __init__(self, portal, dir_name):
        self.portal = portal
        self.dir_name = dir_name

        self.ns_uri = main_namespace_uri + 'cpsskins#'

        self.themes_container = getToolByName(portal, 'portal_themes')

    def updateTheme(self, root, overwrite):
        """Process the elementtree"""

        theme_els = xpath_findall(root, "{%s}theme" % self.ns_uri)
        theme_el = theme_els[0]
        theme_def = self.buildObject(theme_el)

        # save the default theme
        default_theme = self.themes_container.getDefaultThemeName()

        # checking id conflicts
        theme_id = theme_def['id']
        if theme_id in self.themes_container.objectIds():
            if overwrite:
                self.themes_container.manage_delObjects(theme_id)
            else:
                err = "Id conflict: theme %s exists already." % theme_id
                LOG('CPSSkinsImporter.updateTheme', WARNING, err)
                raise ValueError(err)

        self.theme_container = self.createObject(
            self.themes_container, theme_def)

        # create a theme skeleton.
        self.theme_container.createThemeSkeleton()

        self.updateLayout(theme_el)
        self.updateStyles(theme_el)
        self.updatePalettes(theme_el)
        self.updateIcons(theme_el)
        self.updateBackgrounds(theme_el)
        self.updateThumbnails(theme_el)

        # reset the default theme
        self.themes_container.setDefaultTheme(default_theme)

    def updateLayout(self, parent):
        """Build the layout, i.e. pages, page blocks, etc."""
        layout_file = self.getRef(self.ns_uri, 'cpsskinslayout', parent)
        if layout_file:
            PageImporter(self.portal, layout_file,
                self.dir_name, self.theme_container).importFile()

    def updateStyles(self, parent):
        """Build the styles."""
        style_file = self.getRef(self.ns_uri, 'cpsskinsstyles', parent)
        if style_file:
            StyleImporter(self.portal, style_file,
                self.dir_name, self.theme_container).importFile()

    def updatePalettes(self, parent):
        """Build the palettes."""
        palette_file = self.getRef(self.ns_uri, 'cpsskinspalettes', parent)
        if palette_file:
            PaletteImporter(self.portal, palette_file, self.dir_name,
                self.theme_container).importFile()

    def updateIcons(self, parent):
        """Build the icons"""
        icon_file = self.getRef(self.ns_uri, 'cpsskinsicons', parent)
        if icon_file:
            ImageImporter(self.portal, icon_file, self.dir_name,
                'icons', self.theme_container).importFile()

    def updateBackgrounds(self, parent):
        """Build the backgrounds."""
        background_file = self.getRef(self.ns_uri, 'cpsskinsbackgrounds', parent)
        if background_file:
            ImageImporter(self.portal, background_file, self.dir_name,
                'backgrounds', self.theme_container).importFile()

    def updateThumbnails(self, parent):
        """Build the thumbnails."""
        thumbnail_file = self.getRef(self.ns_uri, 'cpsskinsthumbnails', parent)
        if thumbnail_file:
            ImageImporter(self.portal, thumbnail_file, self.dir_name,
                'thumbnails', self.theme_container).importFile()
#
# CPSSkins Page Importer
#
class PageImporter(IOBase, Importer):

    def __init__(self, portal, file_name, dir_name, theme_container):
        self.portal = portal
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name, self.file_name)
        self.ns_uri = main_namespace_uri + 'cpsskinslayout#'
        self.elementtree_ns_uri = "{%s}" % self.ns_uri
        # adding 2 for surrounding curly braces {} of James Clark's NS syntax
        self.ns_uri_len = len(self.ns_uri) + 2

        self.theme_container = theme_container
        self.ptltool = getToolByName(portal, 'portal_cpsportlets', None)

    def getLayoutTypes(self):
        """Return the list of allowed layout types"""

        return ['page',
                'pageblock',
                'cellblock',
                'cellstyler',
                'cellhider',
                'cellsizer',
                'templet',
                'slot',
               ]

    def importFile(self):
        """Parse the XML file into an elementtree structure"""

        self.log("Importing layout from file " + self.file_path)
        LOG("Importing layout from file", INFO, self.file_path)

        doc = ElementTree(file=self.file_path)
        self.updateLayout(doc.getroot())

    def updateLayout(self, root):
        """Process the elementtree"""

        # pages
        page_els = xpath_findall(root, "{%s}page" % self.ns_uri)
        for page_el in page_els:
            self.updateObject(self.theme_container, page_el)

        # global portlets
        importer = PortletImporter(self.portal, self.file_name, self.dir_name, self.ns_uri) 
        if self.ptltool is None:
            self.log("CPSPortlets is not installed. Global portlets will not be imported")
            LOG("CPSSkinsImporter: CPSPortlets is not installed. Global portlets will not be imported",
                INFO, self.file_path)
        else:
            portlet_els = xpath_findall(root, "{%s}portlet" % self.ns_uri)
            for portlet_el in portlet_els:
                importer.buildPortlet(
                    folder=None,
                    portlet_el=portlet_el,
                    restore_id=1)

    def updateObject(self, container, el):
        """Process the elements recursively"""

        object_def = self.buildObject(el)
        object = self.createObject(container, object_def)

        # images
        if object.meta_type == 'Image Box Templet':
            image_els = xpath_findall(el, "{%s}image" % self.ns_uri)
            self.buildImageFile(object, image_els[0])
            # i18n images
            i18nimage_els = xpath_findall(el, "{%s}i18nimage" % self.ns_uri)
            for i18nimage_el in i18nimage_els:
                self.buildImageFile(object, i18nimage_el)

        # flash files
        if object.meta_type == 'Flash Box Templet':
            flash_els = xpath_findall(el, "{%s}flash" % self.ns_uri)
            self.buildFlashFile(object, flash_els[0])


        # parse all children
        layout_types = self.getLayoutTypes()
        for child_el in [el2 for el2 in xpath_findall(el, "*")
                         if el2.tag.startswith(self.elementtree_ns_uri)]:
            child_name = child_el.tag[self.ns_uri_len:]
            if child_name not in layout_types:
                continue
            # process the child element
            self.updateObject(object, child_el)


    def buildFlashFile(self, object, el):
        content_type = el.get('content_type')
        data_file_rpath = el.get('ref')
        data_file_path = os.path.join(CLIENT_HOME, self.dir_name, data_file_rpath)
        file = open(data_file_path, 'rb')
        data, size = object._read_data(file)
        object.update_data(data, content_type, size)
        file.close()


    def buildImageFile(self, object, el):
        id = el.get('id')
        content_type = el.get('content_type')
        title = el.get('title')
        data_file_rpath = el.get('ref')
        data_file_path = os.path.join(CLIENT_HOME, self.dir_name, data_file_rpath)
        data_file = open(data_file_path, 'rb')

        if id.startswith('i18n_image'):
            f = Image(id, title, data_file, content_type=content_type)
            object._setObject(id, f)
        else:
            object.manage_upload(data_file, content_type)

#
# CPSSkins Palette Importer
#

class PaletteImporter(IOBase):

    def __init__(self, portal, file_name, dir_name, theme_container):
        self.portal = portal
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name, self.file_name)
        self.ns_uri = main_namespace_uri + 'cpsskinspalettes#'
        self.elementtree_ns_uri = "{%s}" % self.ns_uri
        # adding 2 for surrounding curly braces {} of James Clark's NS syntax
        self.ns_uri_len = len(self.ns_uri) + 2

        self.theme_container = theme_container

    def importFile(self):
        """Parse the XML file into an elementtree structure"""

        self.log("Importing palettes from file " + self.file_path)
        LOG("Importing palettes from file", INFO, self.file_path)

        doc = ElementTree(file=self.file_path)
        self.updatePalettes(doc.getroot())

    def updatePalettes(self, root):
        """Process the elementtree"""

        palette_els = xpath_findall(root, "{%s}palette" % self.ns_uri)
        palettes = []
        for el in palette_els:
            palette_def = self.buildPalette(el)
            if palette_def:
                palettes.append(palette_def)
        self.createPalettes(palettes)

    def buildPalette(self, el):
        """Build a schema definition"""

        return {'type': el.get('type'),
                'title': el.get('title'),
                'value': el.get('value'),
               }

    #
    # Palettes installation
    #
    def createPalettes(self, palettes):
        """Add palettes"""

        palettes_folder = self.theme_container.getPalettesFolder()
        existing_palettes = palettes_folder.objectValues()
        palette_titles = [getattr(p, 'title') for p in existing_palettes]

        for palette in palettes:
            prop_dict = {'type_name': palette['type'],
                         'title': palette['title'],
                         'value': palette['value'],
                        }
            self.theme_container.addPortalPalette(**prop_dict)

#
# CPSSkins Style Importer
#

class StyleImporter(IOBase):

    def __init__(self, portal, file_name, dir_name, theme_container):
        self.portal = portal
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name, self.file_name)
        self.ns_uri = main_namespace_uri + 'cpsskinsstyles#'
        self.elementtree_ns_uri = "{%s}" % self.ns_uri
        # adding 2 for surrounding curly braces {} of James Clark's NS syntax
        self.ns_uri_len = len(self.ns_uri) + 2

        self.theme_container = theme_container

    def importFile(self):
        """Parse the XML file into an elementtree structure"""
        LOG("Importing styles from file", INFO, self.file_path)
        doc = ElementTree(file=self.file_path)
        self.updateStyles(doc.getroot())

    def updateStyles(self, root):
        """Process the elementtree"""

        style_els = xpath_findall(root, "{%s}style" % self.ns_uri)
        styles = []
        for el in style_els:
            style_def = self.buildStyle(el)
            if style_def:
                styles.append(style_def)
        self.createStyles(styles)

    def buildStyle(self, el):
        """Build a schema definition"""

        schema_def = {}
        schema_def['title'] = el.get('title')
        schema_def['type'] = el.get('type')

        data = {}
        prop_els = xpath_findall(el, "{%s}field" % self.ns_uri)
        for prop_el in prop_els:
            prop_id = prop_el.get('name')
            prop_value = prop_el.get('value')
            data[prop_id] = prop_value

        schema_def['fields'] = data
        return schema_def

    #
    # Styles installation
    #
    def createStyles(self, styles):
        """Add styles"""

        styles_folder = self.theme_container.getStylesFolder()
        for style in styles:
            prop_dict = {'type_name': style['type'],
                         'title': style['title'],
                        }
            new_style = self.theme_container.addPortalStyle(**prop_dict)
            fields = style['fields']
            new_style.edit(**fields)


#
# CPSSkins Image Importer
#

class ImageImporter(IOBase):

    def __init__(self, portal, file_name, dir_name, category, theme_container):
        self.portal = portal
        self.category = category
        self.file_name = file_name
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, self.dir_name, self.file_name)
        self.ns_uri = main_namespace_uri + 'cpsskinsimages#'
        self.elementtree_ns_uri = "{%s}" % self.ns_uri
        # adding 2 for surrounding curly braces {} of James Clark's NS syntax
        self.ns_uri_len = len(self.ns_uri) + 2

        self.theme_container = theme_container
        self.image_dir = getattr(theme_container, category, None)

    def importFile(self):
        """Parse the XML file into an elementtree structure"""

        self.log("Importing images from file" + self.file_path)
        LOG("Importing images from file", INFO, self.file_path)

        doc = ElementTree(file=self.file_path)
        self.updateImages(doc.getroot())

    def updateImages(self, root_el):
        image_els = xpath_findall(root_el, "{%s}image" % self.ns_uri)
        for image_el in image_els:
            self.buildImage(image_el)

    def buildImage(self, image_el):
        if self.image_dir is None:
            return
        id = image_el.get('id')
        content_type = image_el.get('content_type')
        title = image_el.get('title')
        data_file_rpath = image_el.get('ref')
        data_file_path = os.path.join(CLIENT_HOME, self.dir_name, data_file_rpath)
        data_file = open(data_file_path, 'rb')
        f = Image(id, title, data_file, content_type=content_type)
        self.image_dir._setObject(id, f)
