from cloudify import ctx

ctx.logger.info('log and fail during install!')
raise Exception
