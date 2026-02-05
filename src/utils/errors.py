from discord.ext.commands import CommandError

class AWBWDimensionsError(CommandError):
    pass

class InvalidMapError(CommandError):
    pass

class NoLoadedMapError(CommandError):
    pass

class UnimplementedError(CommandError):
    pass

class FileSaveFailureError(CommandError):
    pass
