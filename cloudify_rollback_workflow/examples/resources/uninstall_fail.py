from cloudify import ctx

ctx.logger.info('log and fail during uninstall!')
raise Exception
