# Cloudify Utilities: Cloudify FTP

Upload files by ftp to remote host. See [example](examples/upload_ftp.yaml).

Node properties for `cloudify.nodes.ftp`:
* `resource_config`: connection settings:
  * `user`: The login credentials for ftp server.
  * `password`: Optional, ftp password.
  * `ip`: Optional, device ip.
  * `port`: Optional, ftp port. Default: 21
  * `ignore_host`: Optional, ignore host in ftp response.
  * `tls`: Optional, use tls connection to ftp.
* `raw_files`: dictionary where key is new filename on remote host,
  value is path to raw file in blueprint directory.
* `files`: dictionary where key is new filename on remote host,
  value is file content.
