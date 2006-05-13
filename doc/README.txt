==============
What is CPSIO?
==============

:Revision: $Id$

.. sectnum::    :depth: 4
.. contents::   :depth: 4


CPSIO is a framework and set of plugins for exporting and
importing data from/to existing CPS sites. Data is exported as XML
files stored in a ZIP archive. These XML files use our own
CPS-specific vocabulary. This vocabulary is described by a set of
`relax-ng schemas`_.

.. _`relax-ng schemas`:
    http://www.oasis-open.org/committees/relax-ng/spec-20011203.html

The current version of CPSIO offers two plug-ins:

- CPS3Exporter: used to export data from a CPS3 site

- CPS3Importer: used to import data from a CPS3 site

These two plug-ins make it possible to export and import back the
following data and settings:

- Portal type definitions

- Schema definitions

- Layout definitions

- Widget type definitions

- Workflow definitions

- Vocabulary definitions

- Site hierarchy (workspaces, sections, ...) plus associated local
  roles and boxes

- CPS documents (including attached (binary) files which are
  exported as stand-alone files which can be manipulated using the
  appropriate viewer/editor) + workflow history

A preview of a third plug-in exporting Plone 2 data that can then
be imported in a CPS 3 site is also included. This plug-in is
still under development and should be considered alpha software.

Other plugins could be developed, e.g. to export CPS2 site data
using the already defined XML vocabulary. This data could then be
handled by CPS3Importer and imported in a CPS3 site.


Installation Procedure
======================

- If your Zope instance is 2.6.x (i.e. if it uses python2.1), make
  sure pyexpat and expat are correctly installed (if not, you can
  install them by downloading the XML package for Python (PyXML
  [1]) and installing it (both build and install) [1]
  http://pyxml.sourceforge.net
  
- Put CPSIO in your Products directory

- If ElementTree is not installed on your Zope instance:

  + Go to CPSIO/elementtree

  + Run::

        $ python setup.py build

    then::

        $ python setup.py install

    with the python interpreter used by your Zope instance
    (e.g. ``/opt/Zope-2.7/bin/python``)
    
- Make sure you have a recent version of CPSInstaller installed
  (e.g. the one included in CPS 3.0.2 is too old)
  
- Restart your Zope server.

- In the ZMI, go to the CPS portal's root.

- Install CPSIO in your CPS site.  Use either of the following:

  + Use an external method -- Instantiate a new External Method
    with the following parameters::

        id=cpsio_installer (or anything else)
        title = anything you want (including nothing)
        module name=CPSIO.install
        function name=install

    Then run the method by clicking on the 'Test' tab.

  + Or, in your CPS site in the ZMI, use ``portal_quickinstaller``.


Exporting from CPS 3
====================

- Template export_from_cps3 gives you access to all available
  exporters this template is accessed by clicking on the 'XML
  Export' action in the 'Portal actions' box.

  (e.g. ``http://example.org/cps/export_from_cps3``)

- If you chose to export to a file named foo, this will create a
  ZIP archive in your Zope instance's ``var/`` directory, named
  foo.zip and containing a set of files following this pattern:

  + foo/index (main summary file with links to sub-folders and
    other files)

  + foo/documents (all document instances)

  + foo/documents_files (directory containing all images, attached
    files. etc.)

  + foo/hierarchy (all folder instances and associated local
    role/box settings)

  + foo/layouts (all layout definitions)

  + foo/portal_types (all portal type definitions)

  + foo/schemas (all schema definitions)

  + foo/vocabularies (all vocabularies)

  + foo/workflows (all workflow definitions)


Importing from CPS 3
====================

- The ZIP archive should be placed in your zope instance's import/
  directory

- Template import_from_cps3 gives you access to all available
  importers this template is accessed by clicking on the 'XML
  Import' action in the 'Portal actions' box.
    
  (e.g. ``http://example.org/cps/import_from_cps3``)

- Be sure to specify the main ZIP file in the import form's file
  field (no matter what you want to import) : e.g. foo.zip.


Exporting from Plone 2
======================

Note that at the moment only a few things can be exported from a
Plone 2 site.

- Requirements - your Plone instance must have the following
  Products installed :

  + CPSIO

  + CPSInstaller (needed to install CPSIO)

- In the ZMI, go to the Plone portal's root

- Instantiate a new External Method with the following parameters::

      id=cpsio_installer (or anything else)
      title = anything you want (including nothing)
      module name=CPSIO.install
      function name=install

- Run the method by clicking on the 'Test' tab.

- Direct your browser (or create an action) to a URL pointing at
  template cpsio_exporter_chooser, like::

        http://example.org/plone/cpsio_exporter_chooser

  This template gives you access to all available exporters,
  including the Plone 2 exporter. Select it, and you will be
  presented with its export option panel.


Unit tests
==========

- CPSIO comes with a battery of unit tests that test the whole
  export/import process and compare the results (before and after
  export/import). These tests are based on a CPSDefault site with
  some content added programatically.

  To run the tests, go to CPSIO/tests and run::

      $ make test

  If you get an error stating that elementtree.ElementTree could
  not be imported, try to delete the CPSIO/elementtree directory
  (make sure you have installed ElementTree properly before doing
  this).

