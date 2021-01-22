import os
import aiofiles
import json
import logging
import datetime

# Add the command logger
logger = logging.getLogger("cmdLogger")

prefix = "t:"

# Check if any tournaments in upcoming.dat are no longer upcoming
async def cleanUpcoming(guildID):
    f = await aiofiles.open(f"../data/servers/{guildID}/upcoming.dat")
    upcoming = await f.read()
    await f.close()

    upcoming = json.loads(upcoming)
    upcomingDup = upcoming.copy()
    for event in upcoming:
        dTimeObj = datetime.datetime.strptime(upcoming[event], "%Y/%m/%d %H:%M")
        if dTimeObj < datetime.datetime.now():
            upcomingDup.pop(event)

    upcoming = json.dumps(upcomingDup)

    f = await aiofiles.open(f"../data/servers/{guildID}/upcoming.dat", "w+")
    await f.write(upcoming)
    await f.close()

# If user isn't registered, create a template user file
async def registerUser(userID):
    existingUsers = os.listdir("../data/users")
    if str(userID) in existingUsers:
        return

    bareData = {"tOwned": [], "tJoined": [], "tWins": 0, "mWins": 0}

    bareData = json.dumps(bareData)
    f = await aiofiles.open(f"../data/users/{userID}.dat", "w+")
    await f.write(bareData)
    await f.close()