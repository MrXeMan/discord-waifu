import os.path
import threading

from main import utils


class DeletionReason:
    MANUAL = "File was deleted by user with a command."
    AUTOMATIC = "File was deleted by a garbage disposal unit."


class Core(utils.Core):
    core_name = "scheduler"
    def __init__(self, terminate_signal: threading.Event):
        super().__init__(terminate_signal)
        self.__schedule: list[tuple[str, DeletionReason | str]] = []  # List of files to delete, contains pairs of: file, cause of deletion
        self.__loop_count = 0  # loop count
        self.__locked = False

    async def call(self):
        self.set()
        await self.__get_deleted()
        await super().call()

    async def loop(self):
        if self.__loop_count % (15 * 60):
            await self.clear_scheduler()
            self.__loop_count = -1
        self.__loop_count += 1

    async def stay_alive(self):
        await super().stay_alive()
        self.logger.info("Scheduler is being shut down. Running file deletion...")
        await self.__delete()
        self.logger.info("Scheduler has shut down.")

    def delete_file(self, file: str, reason: DeletionReason | str, no_rename: bool = False):
        if os.path.exists(file):
            if not no_rename:
                os.rename(file, f"{file}.deleted")
                self.__schedule.append((f"{file}.deleted", reason))
            else:
                self.__schedule.append((f"{file}", reason))
        else:
            from main import exceptions
            raise exceptions.DeletionFileNotExists

    async def __get_deleted(self):
        """
        Gets all .deleted files from every directory.
        """
        for curdir, subfolders, files in os.walk(""):
            for file in files:
                if file.endswith(".deleted"):
                    self.delete_file(os.path.join(curdir, file), DeletionReason.AUTOMATIC, no_rename=True)

    async def clear_scheduler(self):
        if not self.__locked:
            self.__locked = True
            await self.__log_updater()
            await self.__delete()
            self.__locked = False

    async def __log_updater(self):
        """
        Updates scheduler's logs to represent what files will it delete.
        :return:
        """
        for file, reason in self.__schedule:
            self.logger.info(f"{file} - {reason}")

    async def __delete(self):
        """
        Deletes every file in the scheduler.
        global_variaables.py contains a switch if this should work.
        :return:
        """
        from main import global_variables
        if not global_variables.no_delete:
            while len(self.__schedule) > 0:
                pair = self.__schedule[0]
                file = pair[0]
                if os.path.exists(file):
                    os.remove(file)
                    self.__schedule.remove(pair)
                else:
                    from main import exceptions
                    raise exceptions.DeletionFileNotExists