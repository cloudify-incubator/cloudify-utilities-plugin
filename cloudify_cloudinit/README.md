# Cloudify Utilities: Cloud-Init

Cloud-Init is the standard for configuration of cloud instances. See [examples](http://cloudinit.readthedocs.io/en/latest/topics/examples.html).

### v1.9.3 extension: external files/jinja2 templates in write_files.content

To use files from blueprint directory in resource_config -> write_files ->
content, it has to be defined as a dictionary which may contain three keys:
* `resource_type`: if it's filled with string "file_resource", the plugin
will be looking for resources under the path defined in `resource_name`,
* `resource_name`: defines the path, where the resource resides,
* `template_variables`: if not empty, this dictionary is being used to fill
the resource content (jinja2 template) with variables.
