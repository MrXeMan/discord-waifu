import os


async def call_async():
    from main import global_variables
    from removalScheduler.core import DeletionReason
    for curdir, subfolders, files in os.walk(".logs"):
        for file in files:
            if "current" in file:
                continue
            global_variables.scheduler.delete_file(os.path.join(curdir, file), DeletionReason.MANUAL)
    await global_variables.scheduler.clear_scheduler()