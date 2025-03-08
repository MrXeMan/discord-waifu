import utils


class Core(utils.Core):
    async def call(self):
        print("Starting Generation!")
        await super().call()

    async def loop(self):
        print("Looped generation!")

    async def stay_alive(self):
        await super().stay_alive()
        print("Stopped Generation!")
