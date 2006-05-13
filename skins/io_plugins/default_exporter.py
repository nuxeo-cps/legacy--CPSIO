##parameters=export_class=None, export_template=None, export_file_name=None, REQUEST=None
# $Id$

if not export_file_name and REQUEST is not None:
    return getattr(context, export_template)(error_msg='err_file',
                                             io_class=export_class,
                                             template=export_template)

io_tool = context.portal_io
exporter = io_tool.getExportPlugin(export_class,
                                   context.portal_url.getPortalObject())

options = [option_name for option_name, option_set in REQUEST.form.items()
           if option_set == 'on']

try:
    exporter.setOptions(export_file_name, options=options)
    exporter.export()
    if REQUEST is not None:
        psm = 'cpsio_psm_export_successful'
        return getattr(context, 'display_log_messages')(log=exporter.logResult(),
                                                        portal_status_message=psm)

except ValueError, err:
    if REQUEST is not None:
        return getattr(context, 'display_log_messages')(log=exporter.logResult(),
                                                        portal_status_message=str(err))

