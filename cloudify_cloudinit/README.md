# Cloudify Utilities: Cloud-Init

Cloud-Init is the standard for configuration of cloud instances. See [examples](http://cloudinit.readthedocs.io/en/latest/topics/examples.html).

### v1.9.3 extension: external_content

To use files from blueprint directory in resource_config -> write_files ->
content, `external_content` property has to be set to `true`. Then, it will
be possible to use path to the file under `content` key, besides passing
the whole script.
