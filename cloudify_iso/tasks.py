import os

import cloudify_common_sdk.iso9660 as iso9660
from cloudify.decorators import operation


def _get_parameters(properties, kwargs):
    for k, v in properties.items():
        if k not in kwargs:
            kwargs[k] = v

    return kwargs


@operation(resumable=True)
def modify_iso(ctx, **kwargs):
    parameters = _get_parameters(ctx.node.properties, kwargs)
    log = 'ISO: {0} will be created based on {1} with new directories:' \
          '\n{2}\nand new files:\n{3}'
    output_iso_path = parameters.get('output_iso_path')
    iso_path = parameters.get('iso_path')
    new_directories = parameters.get('new_directories')
    new_files = parameters.get('new_files')
    output_iso_path = output_iso_path if output_iso_path else\
        '{0}.modified'.format(iso_path)
    ctx.logger.info(log.format(
        output_iso_path, iso_path, new_directories, new_files)
    )

    iso9660.modify_iso(
        iso_path=iso_path,
        output_iso_path=output_iso_path,
        new_directories=new_directories,
        new_files=new_files
    )
    ctx.instance.runtime_properties['modified_iso_path'] = output_iso_path


@operation(resumable=True)
def delete_iso(ctx):
    file_path = ctx.instance.runtime_properties.get('modified_iso_path')
    os.remove(file_path)
    ctx.logger.info('{0} removed'.format(file_path))
