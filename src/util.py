import os
import aiofiles
import json
import logging
from datetime import datetime, timezone
import discord
import termtables
import math
import random
import pytz

# Add the command logger
logger = logging.getLogger("cmdLogger")

# Generate a dictionary of timezone abbreviations to full timezone names. E.g. "PST": "US/Pacific".
# This is because pytz.timezone() only takes full timezone names but we want users to be able to input tz names such as PST
timezoneLookup = dict([(pytz.timezone(x).localize(datetime.now()).tzname(), x) for x in pytz.all_timezones])


prefix = "t:"

# Check if any tournaments in upcoming.json are no longer upcoming
async def cleanUpcoming(guildID):
    f = await aiofiles.open(f"../data/servers/{guildID}/upcoming.json")
    upcoming = await f.read()
    await f.close()

    upcoming = json.loads(upcoming)
    upcomingDup = upcoming.copy()
    for event in upcoming:
        dTimeObj = datetime.strptime(upcoming[event], "%Y/%m/%d %H:%M")
        if dTimeObj < datetime.now():
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

async def genOwnedPage(guildID, userID, **kwargs):
    f = await aiofiles.open(f"../data/users/{userID}.json")
    userData = await f.read()
    await f.close()

    userData = json.loads(userData)

    tOwned = userData["tOwned"]

    owned = []
    for tourney in tOwned:
        if tourney.split("/")[0] == str(guildID):
            owned.append(tourney.split("/")[1])

    # Load upcoming tournaments into list of lists for termtables to use
    tableList = []
    i = 0
    tournamentIDs = []
    page = 1
    for tID in owned:
        i += 1

        if i < ((page - 1) * 5) + 1:
            continue

        if i > page * 5:
            break

        f = await aiofiles.open(f"../data/servers/{guildID}/{tID}.json")
        tournament = await f.read()
        await f.close()
        tournament = json.loads(tournament)

        try:

            if i % 5 == kwargs["selection"]:
                tournament["name"] = "*" + tournament["name"]

        except:
            pass

        tournamentList = [await intToEmoji(i), tournament["name"], f"{tournament['dTime']} UTC",
                          f"{len(tournament['players'])}/{tournament['limit']}"]
        tableList.append(tournamentList)

        tournamentIDs.append(tID)

    footer = f"{page}/{math.ceil(len(owned) / 5)}"
    # Generate an ASCII table using termtables
    desc = termtables.to_string(header=["ID", "Name", "Date/Time", "Players"],
                                style=termtables.styles.markdown,
                                data=tableList)

    desc = desc.splitlines()
    desc[0] = desc[0].replace("|", " ")
    desc[1] = desc[1].replace("|", "-")

    desc = "\n".join(desc)

    em = discord.Embed(title="Owned Tournaments", description=f"```{desc}```", colour=255)
    return (em, tournamentIDs)

# If user isn't registered, create a template user file
async def registerUser(userID):
    existingUsers = os.listdir("../data/users")
    if f"{str(userID)}.json" in existingUsers:
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

async def deleteTournament(userID, tournamentID, guildID):
    f = await aiofiles.open(f"../data/users/{userID}.json")
    old = await f.read()
    await f.close()

    old = json.loads(old)
    old["tOwned"].pop(old["tOwned"].index(f"{guildID}/{tournamentID}"))

    f = await aiofiles.open(f"../data/users/{userID}.json", "w")
    await f.write(json.dumps(old))
    await f.close()\

    f = await aiofiles.open(f"../data/servers/{guildID}/upcoming.json")
    old = await f.read()
    await f.close()

    old = json.loads(old)
    del old[tournamentID]

    f = await aiofiles.open(f"../data/servers/{guildID}/upcoming.json", "w")
    await f.write(json.dumps(old))
    await f.close()

    f = await aiofiles.open(f"../data/servers/{guildID}/{tournamentID}.json")
    tournament = await f.read()
    await f.close()

    tournament = json.loads(tournament)
    for user in tournament["players"]:
        f = await aiofiles.open(f"../data/users/{user}.json")
        old = await f.read()
        await f.close()

        old = json.loads(old)
        old["tJoined"].pop(old["tJoined"].index(f"{guildID}/{tournamentID}"))

        f = await aiofiles.open(f"../data/users/{user}.json", "w")
        await f.write(json.dumps(old))
        await f.close()

    os.remove(f"../data/servers/{guildID}/{tournamentID}.json")

async def editTournament(message, name, date, time, tz, limit, tourneyID):
    global timezoneLookup

    dTime = date + time
    try:
        # Generate a timezone agnostic datetime object from the user's input
        dTimeObj = datetime.strptime(dTime, "%Y/%m/%d%H:%M")
        # Get a timezone object from the shortcode provided by the user
        oldTZ = pytz.timezone(timezoneLookup[tz])
        # Add a datetime to the timezone object
        oldTZ = oldTZ.localize(dTimeObj)
        # Convert the timezone/datetime object to a datetime object in UTC
        dTimeObj = oldTZ.astimezone(timezone.utc)

    except ValueError:
        logger.debug("Invalid datetime")
        em = discord.Embed(title="Error",
                           description="Invalid date/time. Please make sure it's in this format: YYYY/MM/DD HH:MM TZ",
                           colour=16711680)
        await message.channel.send(embed=em)
        return

    except KeyError:
        logger.debug("Invalid timezone")
        em = discord.Embed(title="Error", description="Invalid timezone.", colour=16711680)
        await message.channel.send(embed=em)
        return

    dTime = datetime.strftime(dTimeObj, "%Y/%m/%d %H:%M")

    os.makedirs(f"../data/servers/{message.guild.id}/", exist_ok=True)

    tourney = {"name": name, "dTime": dTime, "players": [], "limit": limit}

    f = await aiofiles.open(f"../data/servers/{message.guild.id}/{tourneyID}.json")
    old = await f.read()
    await f.close()
    old = json.loads(old)
    tourney["players"] = old["players"]

    em = discord.Embed(title="Tournament Edited", colour=65280)
    em.add_field(name="Name", value=name, inline=False)
    em.add_field(name="Date", value=dTime.split(" ")[0], inline=False)
    em.add_field(name="Time", value=f"{dTime.split(' ')[1]} UTC", inline=False)

    await message.channel.send(embed=em)

    # Convert dictionary to json string
    tourney = json.dumps(tourney)

    f = await aiofiles.open(f"../data/servers/{message.guild.id}/upcoming.json")
    oldData = await f.read()
    await f.close()

    upcoming = json.loads(oldData)
    upcoming[tourneyID] = dTime

    upcoming = json.dumps(upcoming)

    f = await aiofiles.open(f"../data/servers/{message.guild.id}/upcoming.json", "w+")
    await f.write(upcoming)
    await f.close()

    await cleanUpcoming(message.guild.id)

    f = await aiofiles.open(f"../data/servers/{message.guild.id}/{tourneyID}.json", "w+")
    await f.write(tourney)
    await f.close()
