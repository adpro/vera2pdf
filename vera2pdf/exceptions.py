class AppError(Exception):
    pass

# No input parameter to programme
class NoInputParameterError(AppError):
    pass

# changed number of lines header, changed format of programme table and so on
class WrongProgrammeFormatError(AppError):
    pass

class LibreOfficeNotFoundError(AppError):
    pass