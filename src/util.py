import os
import aiofiles
import json
import logging
import datetime
import discord
import termtables
import math
import random

# Add the command logger
logger = logging.getLogger("cmdLogger")

prefix = "t:"

# Check if any tournaments in upcoming.json are no longer upcoming
async def cleanUpcoming(guildID):
    f = await aiofiles.open(f"../data/servers/{guildID}/upcoming.json")
    upcoming = await f.read()
    await f.close()

    upcoming = json.loads(upcoming)
    upcomingDup = upcoming.copy()
    for event in upcoming:
        dTimeObj = datetime.datetime.strptime(upcoming[event], "%Y/%m/%d %H:%M")
        if dTimeObj < datetime.datetime.now():
            upcomingDup.pop(event)

    upcoming = json.dumps(upcomingDup)

    f = await aiofiles.open(f"../data/servers/{guildID}/upcoming.json", "w+")
    await f.write(upcoming)
    await f.close()


async def genUpcomingPage(page, guildID):
    f = await aiofiles.open(f"../data/servers/{guildID}/upcoming.json")
    upcoming = await f.read()
    await f.close()
    upcoming = json.loads(upcoming)

    # Load upcoming tournaments into list of lists for termtables to use
    tableList = []
    i = 0
    tournamentIDs = []
    for key in upcoming:
        i += 1

        if i < ((page - 1) * 5) + 1:
            continue

        if i > page * 5:
            break

        f = await aiofiles.open(f"../data/servers/{guildID}/{key}.json")
        tournament = await f.read()
        await f.close()
        tournament = json.loads(tournament)

        tournamentList = [await intToEmoji(i), tournament["name"], f"{tournament['dTime']} UTC",
                          f"{len(tournament['players'])}/{tournament['limit']}"]
        tableList.append(tournamentList)

        tournamentIDs.append(key)

    footer = f"{page}/{math.ceil(len(upcoming) / 5)}"
    # Generate an ASCII table using termtables
    desc = termtables.to_string(header=["ID", "Name", "Date/Time", "Players"],
                                style=termtables.styles.markdown,
                                data=tableList)

    desc = desc.splitlines()
    desc[0] = desc[0].replace("|", " ")
    desc[1] = desc[1].replace("|", "-")

    desc = "\n".join(desc)

    em = discord.Embed(title="Upcoming Tournaments", description=f"```{desc}```", colour=255)
    em.set_footer(text=footer)
    return (em, tournamentIDs)


# If user isn't registered, create a template user file
async def registerUser(userID):
    existingUsers = os.listdir("../data/users")
    if str(userID) in existingUsers:
        return

    bareData = {"tOwned": [], "tJoined": [], "tWins": 0, "mWins": 0}

    bareData = json.dumps(bareData)
    f = await aiofiles.open(f"../data/users/{userID}.json", "w+")
    await f.write(bareData)
    await f.close()


# Turn integer into string of emojis representing that integer
async def intToEmoji(myInt):
    emoji = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    myInt = str(myInt)
    emojiInt = ""
    for char in myInt:
        emojiInt = emojiInt + emoji[int(char)]
    return emojiInt

async def joinTournament(userID, tournamentID, guildID):
    f = await aiofiles.open(f"../data/servers/{guildID}/{tournamentID}.json")
    old = await f.read()
    await f.close()

    old = json.loads(old)
    tournamentName = old["name"]
    if int(userID) in old["players"]:
        old["players"].pop(old["players"].index(userID))

        f = await aiofiles.open(f"../data/servers/{guildID}/{tournamentID}.json", "w")
        await f.write(json.dumps(old))
        await f.close()

        f = await aiofiles.open(f"../data/users/{userID}.json")
        old = await f.read()
        await f.close()

        old = json.loads(old)
        old["tJoined"].pop(old["tJoined"].index(f"{guildID}/{tournamentID}"))

        f = await aiofiles.open(f"../data/users/{userID}.json", "w")
        await f.write(json.dumps(old))
        await f.close()

        return 2, tournamentName

    if len(old["players"]) >= int(old["limit"]):
        return 0, tournamentName

    old["players"].append(userID)

    f = await aiofiles.open(f"../data/servers/{guildID}/{tournamentID}.json", "w")
    await f.write(json.dumps(old))
    await f.close()

    f = await aiofiles.open(f"../data/users/{userID}.json")
    old = await f.read()
    await f.close()

    old = json.loads(old)

    old["tJoined"].append(f"{guildID}/{tournamentID}")

    f = await aiofiles.open(f"../data/users/{userID}.json", "w")
    await f.write(json.dumps(old))
    await f.close()

    return 1, tournamentName
