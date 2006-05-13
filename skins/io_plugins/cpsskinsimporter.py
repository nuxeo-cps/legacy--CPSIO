##parameters=import_class=None, import_template=None, import_file_name=None, REQUEST=None

if not import_file_name and REQUEST is not None:
    return getattr(context, import_template)(error_msg='err_file',
                                             io_class=import_class,
                                             template=import_template)

io_tool = context.portal_io
importer = io_tool.getImportPlugin(import_class,
                                   context.portal_url.getPortalObject())

options = [option_name for option_name, option_set in REQUEST.form.items()
           if option_set == 'on']

# do not assume that CPSSkins is installed
try:
    tmtool = context.portal_themes
except AttributeError, err:
    return getattr(context, 'display_log_messages')(log=importer.logResult(),
           portal_status_message='cpsio_psm_cpsskins_not_installed')

try:
    importer.setOptions(import_file_name, options=options)
    importer.importFile()
    importer.finalize()
    if REQUEST is not None:
        psm = 'cpsio_psm_import_successful'
        return getattr(context, 'display_log_messages')(log=importer.logResult(),
                                                        portal_status_message=psm)

except ValueError, err:
    if REQUEST is not None:
        return getattr(context, 'display_log_messages')(log=importer.logResult(),
                                                        portal_status_message=str(err))

