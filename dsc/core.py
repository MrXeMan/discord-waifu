import utils


class Core(utils.Core):
    async def call(self):
        print("Starting Discord Waifu!")
        await super().call()

    async def loop(self):
        print("Looped Discord Waifu!")

    async def stay_alive(self):
        await super().stay_alive()
        print("Stopped Discord Waifu!")