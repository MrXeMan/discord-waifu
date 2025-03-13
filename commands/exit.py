import main.exceptions


def call():
    from main import utils
    from main.global_variables import terminate_signal
    terminate_signal.set()
    raise main.exceptions.EndSignal("Exit command sent an uncaught end signal!")