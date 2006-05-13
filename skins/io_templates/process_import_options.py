##parameters=import_module=None, REQUEST=None

# $Id$

if not import_module and REQUEST is not None:
    return context.import_from_cps3_form(error_message='error_module')

io_tool = context.portal_io
template = io_tool.getImportPluginTemplate(import_module)

return getattr(context, template)(io_class=import_module)
