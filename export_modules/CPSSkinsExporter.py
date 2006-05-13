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
from elementtree.ElementTree import ElementTree, Element, SubElement

from Acquisition import aq_base
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from zLOG import LOG, DEBUG, INFO, WARNING, ERROR

from Products.CMFCore.permissions import ManagePortal
from Products.CMFCore.utils import getToolByName

from Products.CPSIO.BaseExporter import MAIN_NAMESPACE_URI, BaseExporter
from Products.CPSIO.IOBase import IOBase
from Products.CPSIO.export_modules.CPS3Exporter import PortletExporter

class Exporter(BaseExporter):

    options_template = 'cpsskinsexporter_form'
    options_table = []

    security = ClassSecurityInfo()
    security.declareObjectPublic()

    __roles__ = None
    __allow_access_to_unprotected_subobjects__ = 1

    def __init__(self, portal):
        self.portal = portal
        self.ns_uri = MAIN_NAMESPACE_URI + 'cpsskins#'


    security.declareProtected(ManagePortal, 'export')
    def exportFile(self):
        """Main Export"""

        self.log("Exporting to file " + self.file_path)
        LOG("Exporting to file", DEBUG, self.file_path)

        tmtool = self.portal.portal_themes
        options = self.options
        current_theme = filter(lambda x: x.startswith('theme_'), options)
        if len(current_theme) > 0:
            current_theme = current_theme[0][len('theme_'):]
        else:
            current_theme = tmtool.getDefaultThemeName()

        self.theme_container = tmtool.getThemeContainer(theme=current_theme)

        root = self.buildTree()
        doc = ElementTree(root)
        doc.write(self.file_path, encoding="iso-8859-15")
        self.archiveExport()

    def buildTree(self):
        root = Element("{%s}cpsskinsdefinitions" % self.ns_uri)
        self.buildTheme(root)
        return root

    def buildObject(self, parent, object):
        parent.set('id', object.getId())
        parent.set('type', object.meta_type)
        # export the object's attributes
        for field_prop_id, field_prop_value in object.propertyItems():
            # format the property value to a string
            field_prop_type = object.getPropertyType(field_prop_id)
            if field_prop_type in ('multiple selection', 'lines'):
                field_prop_value = ','.join(field_prop_value)
            else:
                field_prop_value = str(field_prop_value)

            el = SubElement(parent, "{%s}field" % self.ns_uri)
            el.set('name', field_prop_id)
            el.set('value', field_prop_value)
            el.set('type', field_prop_type)
        return el

    def buildTheme(self, parent):
        # build the theme object
        el = SubElement(parent, "{%s}theme" % self.ns_uri)
        el2 = self.buildObject(el, object=self.theme_container)
        self.buildPages(el)
        self.buildStyles(el)
        self.buildPalettes(el)
        self.buildIcons(el)
        self.buildBackgrounds(el)
        self.buildThumbnails(el)

    def buildPages(self, parent):
        file_name = PageExporter(self.portal, self.dir_name,
                                 self.theme_container).exportFile()
        el = SubElement(parent, "{%s}cpsskinslayout" % self.ns_uri)
        el.set('ref', file_name)

    def buildStyles(self, parent):
        file_name = StyleExporter(self.portal, self.dir_name,
                                  self.theme_container).exportFile()
        el = SubElement(parent, "{%s}cpsskinsstyles" % self.ns_uri)
        el.set('ref', file_name)

    def buildPalettes(self, parent):
        file_name = PaletteExporter(self.portal, self.dir_name,
                                    self.theme_container).exportFile()
        el = SubElement(parent, "{%s}cpsskinspalettes" % self.ns_uri)
        el.set('ref', file_name)

    def buildIcons(self, parent):
        file_name = ImageExporter(self.portal, self.dir_name, 'icons',
                                  self.theme_container).exportFile()
        el = SubElement(parent, "{%s}cpsskinsicons" % self.ns_uri)
        el.set('ref', file_name)

    def buildBackgrounds(self, parent):
        file_name = ImageExporter(self.portal, self.dir_name, 'backgrounds',
                                  self.theme_container).exportFile()
        el = SubElement(parent, "{%s}cpsskinsbackgrounds" % self.ns_uri)
        el.set('ref', file_name)

    def buildThumbnails(self, parent):
        file_name = ImageExporter(self.portal, self.dir_name, 'thumbnails',
                                  self.theme_container).exportFile()
        el = SubElement(parent, "{%s}cpsskinsthumbnails" % self.ns_uri)
        el.set('ref', file_name)

InitializeClass(Exporter)

#
# CPSSkins Page Exporter
#
class PageExporter(IOBase, Exporter):

    def __init__(self, portal, dir_name, theme_container):
        self.portal = portal
        tmtool = self.portal.portal_themes
        self.theme_container = theme_container
        self.dir_name = dir_name
        self.file_name = 'cpsskins_layout'
        self.file_path = os.path.join(CLIENT_HOME, dir_name, self.file_name)
        self.attachment_dir = self.file_name + '_files'
        self.attachment_dir_path = os.path.join(CLIENT_HOME, dir_name,
                                                self.attachment_dir)
        self.ns_uri = MAIN_NAMESPACE_URI + 'cpsskinslayout#'

    def exportFile(self):
        """Export layout"""

        self.log("Exporting layout to file " + self.file_path)
        LOG("Exporting layout to file", DEBUG, self.file_path)

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
        """Build the elementtree representing all layout elements"""

        root = Element("{%s}layout" % self.ns_uri)
        self.exportPages(self.theme_container, root)
        return root

    def getTypeName(self, meta_type):
        """Return a short type name for a given meta type"""

        mapping = {'Portal Theme': 'theme',
                   'Theme Page': 'page',
                   'Page Block': 'pageblock',
                   'Cell Block': 'cellblock',
                   'Cell Sizer': 'cellsizer',
                   'Cell Styler': 'cellstyler',
                   'Cell Hider': 'cellhider',
                   'Portal Box Group Templet': 'slot',
                  }

        # everything else is a Templet.
        return mapping.get(meta_type, 'templet')

    def exportPages(self, theme_container, parent):
        """Build an elementtree representation of a CPSSkins layout"""

        # global portlets
        self.global_portlets = []


        # export the pages
        for page in theme_container.getPages():
            self.exportObject(object=page,
                              parent=parent,
                              recursive=1)

        # export global portlets
        # portlets used in theme are listed in self.global_portlets
        if len(self.global_portlets) > 0:
            ptltool = getToolByName(theme_container, 'portal_cpsportlets', None)
            if ptltool is None:
                self.log("CPSPortlets is not installed. Global portlets will not be exported")
                LOG("CPSSkinsExporter: CPSPortlets is not installed. Global portlets will not be exported",
                    INFO, self.file_path)
            else:
                portlet_container = ptltool.getPortletContainer(context=None)
                for portlet_id in self.global_portlets:
                    portlet = portlet_container.getPortletById(portlet_id)
                    if portlet is None:
                        continue
                    self.buildPortlet(portlet, parent, self.dir_name, self.ns_uri)

    def buildPortlet(self, portlet, parent, dir_name, ns_uri):

        portlet_id = portlet.id
        el = SubElement(parent, "{%s}portlet" % ns_uri)
        el.set('id', portlet_id)
        el.set('portletType', portlet.portal_type)
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

    def exportObject(self, object, parent, recursive):
        """Build an elementtree representation of a CPSSkins objects"""

        meta_type = object.meta_type
        type = self.getTypeName(meta_type)
        el = SubElement(parent, "{%s}%s" % (self.ns_uri, type))
        self.buildObject(el, object)

        # save binary data as attachement
        if meta_type == 'Image Box Templet':
            self.buildImageData(el, object, 'image')
            if getattr(aq_base(object), 'getI18nImages', None) is not None:
                i18n_img_dict = object.getI18nImages()
                for img in i18n_img_dict.values():
                    self.buildImageData(el, img, 'i18nimage')
            return el

        if meta_type == 'Flash Box Templet':
            self.buildFlashData(el, object, 'flash')

        # global portlets
        if meta_type == 'Portlet Box Templet':
            self.global_portlets.append(object.portlet_id)

        # export sub-objects if the object itself is a container
        if recursive:
            for subobject in object.objectValues():
                self.exportObject(object=subobject,
                                  parent=el,
                                  recursive=1)
        return el

    def buildImageData(self, parent, f, tag):
        el = SubElement(parent, "{%s}%s" % (self.ns_uri, tag))
        image_id = f.getId()
        el.set('id', image_id)
        el.set('ref', "%s/%s" % (self.attachment_dir, image_id))
        el.set('content_type', f.content_type)
        el.set('title', f.title)
        f_path = os.path.join(self.attachment_dir_path, image_id)
        of = open(f_path, 'wb')
        of.write(str(f.data))
        of.flush()
        of.close()

    def buildFlashData(self, parent, f, tag):
        el = SubElement(parent, "{%s}%s" % (self.ns_uri, tag))
        flash_id = f.getId()
        el.set('id', flash_id)
        el.set('ref', "%s/%s" % (self.attachment_dir, flash_id))
        el.set('content_type', f.content_type)
        el.set('title', f.title)
        f_path = os.path.join(self.attachment_dir_path, flash_id)
        of = open(f_path, 'wb')
        of.write(str(f.data))
        of.flush()
        of.close()
#
# CPSSkins Palette Exporter
#
class PaletteExporter(IOBase):

    def __init__(self, portal, dir_name, theme_container):
        self.portal = portal
        tmtool = self.portal.portal_themes
        self.theme_container = theme_container
        self.file_name = 'cpsskins_palettes'
        self.file_path = os.path.join(CLIENT_HOME, dir_name, self.file_name)
        self.ns_uri = MAIN_NAMESPACE_URI + 'cpsskinspalettes#'

    def exportFile(self):
        """Export palettes"""

        self.log("Exporting palettes to file " + self.file_path)
        LOG("Exporting palettes to file", DEBUG, self.file_path)

        root = self.buildTree()
        doc = ElementTree(root)
        doc.write(self.file_path, encoding="iso-8859-15")
        return self.file_name

    def buildTree(self):
        """Build the elementtree representing all palettes"""

        root = Element("{%s}palettes" % self.ns_uri)
        palettedir = self.theme_container.getPalettesFolder()
        for palette_id, palette in palettedir.objectItems():
            self.exportPalette(palette_id, palette, root)
        return root

    def exportPalette(self, palette_id, palette, parent):
        """Build an elementtree representation of a CPSSkins palette"""

        el = SubElement(parent, "{%s}palette" % self.ns_uri)
        el.set('type', palette.meta_type)
        el.set('title', getattr(palette, 'title'))
        el.set('value', getattr(palette, 'value'))


#
# CPSSkins Style Exporter
#
class StyleExporter(IOBase):

    def __init__(self, portal, dir_name, theme_container):
        self.portal = portal
        tmtool = self.portal.portal_themes
        self.theme_container = theme_container
        self.file_name = 'cpsskins_styles'
        self.file_path = os.path.join(CLIENT_HOME, dir_name, self.file_name)
        self.ns_uri = MAIN_NAMESPACE_URI + 'cpsskinsstyles#'

    def exportFile(self):
        """Export styles"""

        self.log("Exporting styles to file " + self.file_path)
        LOG("Exporting styles to file", DEBUG, self.file_path)

        root = self.buildTree()
        doc = ElementTree(root)
        doc.write(self.file_path, encoding="iso-8859-15")
        return self.file_name

    def buildTree(self):
        """Build the elementtree representing all styles"""

        root = Element("{%s}styles" % self.ns_uri)
        styledir = self.theme_container.getStylesFolder()
        for style_id, style in styledir.objectItems():
            self.exportStyle(style_id, style, root)
        return root

    def exportStyle(self, style_id, style, parent):
        """Build an elementtree representation of a CPSSkins style"""

        el = SubElement(parent, "{%s}style" % self.ns_uri)
        el.set('type', style.meta_type)
        el.set('title', getattr(style, 'title'))

        for field_prop_id, field_prop_value in style.propertyItems():
            el2 = SubElement(el, "{%s}field" % self.ns_uri)
            el2.set('name', field_prop_id)
            el2.set('value', str(field_prop_value))

#
# CPSSkins Images Exporter
#
class ImageExporter(IOBase):

    def __init__(self, portal, dir_name, category, theme_container):
        self.portal = portal
        self.category = category
        tmtool = self.portal.portal_themes
        self.theme_container = theme_container
        self.file_name = 'cpsskins_images_' + category
        self.dir_name = dir_name
        self.file_path = os.path.join(CLIENT_HOME, dir_name, self.file_name)
        self.attachment_dir = self.file_name + '_files'
        self.attachment_dir_path = os.path.join(CLIENT_HOME, dir_name,
                                                self.attachment_dir)
        self.ns_uri = MAIN_NAMESPACE_URI + 'cpsskinsimages#'

    def exportFile(self):
        """Export images"""

        self.log("Exporting images to file " + self.file_path)
        LOG("Exporting images to file", DEBUG, self.file_path)

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
        """Build the elementtree representing images"""

        root = Element("{%s}cpsskins%s" % (self.ns_uri, self.category))

        self.buildImages(root)
        return root

    def buildImages(self, root_el):
        try:
            image_dir= self.theme_container[self.category]
        except AttributeError:
            self.log("ImageExporter: Error: %s folder not found" \
                     % self.category)
            LOG("ImageExporter: Error:",ERROR,
                "folder %s not found" % self.category)
            return

        for item in image_dir.objectValues():
            if item.meta_type in ('Image', 'Portal Image'):
                self.buildImage(root_el, item)
            else:
                self.log("ImageExporter: Error: object type %s not supported" \
                         % item.meta_type)
                LOG("ImageExporter: Error:",ERROR,
                    "object type %s not supported" % item.meta_type)

    def buildImage(self, parent, f):
        el = SubElement(parent, "{%s}image" % self.ns_uri)
        image_id = f.id()
        el.set('id', image_id)
        el.set('ref', "%s/%s" % (self.attachment_dir, image_id))
        el.set('content_type', f.content_type)
        el.set('title', f.title)
        f_path = os.path.join(self.attachment_dir_path, image_id)
        of = open(f_path, 'wb')
        of.write(str(f.data))
        of.flush()
        of.close()
