class TerminateSignalMissing(BaseException):
    """
    Exception when terminate signal is missing.
    """
    def __init__(self, message="Terminate signal is None. Please specify the terminate signal."):
        super().__init__(message)


class EndSignal(BaseException):
    """
    Exception used to stop the console.
    """
    def __init__(self, messsage="There is an uncaught end signal!"):
        super().__init__(messsage)


class CoreNameMissing(BaseException):
    """
    Exception when name is missing.
    """
    def __init__(self, message="Core name is None. Please specify the name."):
        super().__init__(message)


class DeletionFileNotExists(BaseException):
    """
    Happens when file given to the scheduler does not exist.
    """
    def __init__(self, message="File in the scheduler does not exist."):
        super().__init__(message)


class IncompleteRequest(BaseException):
    def __init__(self, message="There is an incomplete request!"):
        super().__init__(message)
