##parameters=export_module=None, REQUEST=None

# $Id$

if not export_module and REQUEST is not None:
    return context.export_from_cps3_form(error_message='error_module')

io_tool = context.portal_io
template = io_tool.getExportPluginTemplate(export_module)

return getattr(context, template)(io_class=export_module)
