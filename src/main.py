import discord
import sys

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

# Run bot
client.run(token)
