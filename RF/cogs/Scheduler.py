from datetime import datetime

from nextcord.ext.commands import Cog

from ..bot import RF
from .Bounty import Bounty


class Scheduler(Cog):
    def __init__(self, bot: RF) -> None:
        self.bot = bot


    @Cog.listener()
    async def on_ready(self) -> None:
        schedules = self.bot.SCHEDULER.find()

        for schedule in schedules:
            ID, scheduleType = schedule["_id"].split("-")

            day, month, year, hour, minute, second = schedule["Expired"].split("-")
            expired_time = datetime(year=int(year), month=int(month), day=int(day), hour=int(hour), minute=int(minute), second=int(second))
            guild = self.bot.get_guild(schedule["Guild ID"])

            if scheduleType == "Bounty":
                if expired_time > datetime.now():
                    print(self.bot.scheduler.add_job(Bounty(self.bot).deleteBounty, id=schedule["_id"], args=[guild, int(ID)], next_run_time=expired_time, replace_existing=True))
                else:
                    await Bounty(self.bot).deleteBounty(guild, ID)
                    schedules = self.bot.SCHEDULER.delete_one({"_id": f"{ID}-{scheduleType}"})

        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Scheduler")


def setup(bot):
    bot.add_cog(Scheduler(bot))
