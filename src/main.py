import discord
import sys
import aiofiles
import json
import math
import termtables
import random

import util
import cmds

# Setup logging so discord.py can log
import logging
discordLogger = logging.getLogger("discord")
discordLogger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="../logs/discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
discordLogger.addHandler(handler)

# Setup a logger to log commands registered
logger = logging.getLogger("cmdLogger")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

# Read token from file
file = open("../token.dat")
token = file.read().strip()
file.close()

prefix = "t:"

client = discord.Client()

@client.event
async def on_ready():
    # Delete token out of memory, since the bot is already logged in. Just in case.
    global token
    del token

    logger.info(f"Logged in as {client.user.name}")


@client.event
async def on_message(message):
    global prefix

    # Prevents infinite loops caused by the bot triggering its own commands
    if message.author == client.user:
        return

    # If message doesn't start with the prefix, stop processing
    if not message.content.strip().startswith(prefix):
        return

    if " " in message.content.strip():
        # Separate the command and its parameters into different variables
        cmd, args = message.content.strip().split(" ", 1)
        args = args.split(" ")

    else:  # if command has no arguments, set args to an empty list
        cmd = message.content.strip()
        args = []

    cmd = cmd.replace(prefix, "")

    # If there's no corresponding command function, stop processing
    if f"cmd_{cmd}" not in vars(cmds):
        return

    # If the number of arguments is incorrect, send an error message and stop processing
    cmdFunc = vars(cmds)[f"cmd_{cmd}"]
    cmdArgCount = cmdFunc.__code__.co_argcount-2
    if cmdArgCount != len(args):
        em = discord.Embed(title="Incorrect number of arguments", description=f"Expected {cmdArgCount}, you gave {len(args)}", colour=16711680)
        await message.channel.send(embed=em)
        return

    # Register user if they're not already registered
    await util.registerUser(message.author.id)

    args.insert(0, message)
    args.insert(0, client)
    # Call the command function
    await cmdFunc(*args)

    logger.info(f"{message.author.name}({message.author.id}) -> {message.channel.name}({message.channel.id}): {message.content.strip()}")

@client.event
async def on_reaction_add(reaction, user):
    userID = reaction.message.reference.resolved.author.id
    if user.id != userID:
        return

    await util.cleanUpcoming(reaction.message.guild.id)

    page = int(reaction.message.embeds[0].footer.text.split("/")[0])
    maxPage = int(reaction.message.embeds[0].footer.text.split("/")[1])
    if reaction.emoji == "➡️" and page < maxPage:
        page += 1

    elif reaction.emoji == "⬅️" and page > 1:
        page -= 1

    else:
        return

    f = await aiofiles.open(f"../data/servers/{reaction.message.guild.id}/upcoming.json")
    upcoming = await f.read()
    await f.close()
    upcoming = json.loads(upcoming)

    # Load upcoming tournaments into list of lists for termtables to use
    tableList = []
    i = 0
    for key in upcoming:
        i += 1

        if i < ((page-1)*5)+1:
            continue

        if i > page*5:
            break

        f = await aiofiles.open(f"../data/servers/{reaction.message.guild.id}/{key}.json")
        tournament = await f.read()
        await f.close()
        tournament = json.loads(tournament)

        tournamentList = [await util.intToEmoji(i), tournament["name"], f"{tournament['dTime']} UTC",
                          f"{len(tournament['players'])}/{tournament['limit']}"]
        tableList.append(tournamentList)

    footer = f"{page}/{math.ceil(len(upcoming) / 5)}"
    # Generate an ASCII table using termtables
    desc = termtables.to_string(header=["ID", "Name", "Date/Time", "Players"],
                                style=termtables.styles.markdown,
                                data=tableList)

    desc = desc.splitlines()
    desc[0] = desc[0].replace("|", " ")
    desc[1] = desc[1].replace("|", "-")

    desc = "\n".join(desc)

    em = discord.Embed(title="Upcoming Tournaments", description=f"```{desc}```", colour=random.randint(0, 16777215))
    em.set_footer(text=footer)

    await reaction.message.edit(embed=em, allowed_mentions=discord.AllowedMentions(replied_user=False))
    await reaction.remove(user)


# Run bot
client.run(token)
