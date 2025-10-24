import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

# Get sensitive data from .env
BOT_TOKEN = os.getenv('BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))  # Convert to int since IDs are numbers
USER_ID = int(os.getenv('USER_ID'))    # Convert to int
OUTPUT_FILE = 'user_messages.jsonl'

# Check if environment variables are loaded
if not all([BOT_TOKEN, GUILD_ID, USER_ID]):
    raise ValueError("Missing required environment variables. Check your .env file.")

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print(f'Guild with ID {GUILD_ID} not found.')
        await bot.close()
        return

    # Fetch the user to get their name for the system prompt
    user = await bot.fetch_user(USER_ID)
    if not user:
        print(f'User with ID {USER_ID} not found.')
        await bot.close()
        return

    # Define the system prompt (customize the description as needed)
    SYSTEM_PROMPT = f"[INST] System: You are mimicking {user.name}, a friendly and casual Discord user. Respond as they would in a group chat. \n\n[/INST]"

    messages = []
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).read_message_history:
            try:
                async for message in channel.history(limit=None):  # limit=None for all messages, but beware of rate limits
                    if message.author.id == USER_ID:
                        completion = message.content
                        if message.attachments:
                            urls = ", ".join([att.url for att in message.attachments])
                            completion += f'\nAttachments: {urls}'
                        if completion.strip():  # Skip empty messages
                            msg_dict = {
                                "prompt": SYSTEM_PROMPT,
                                "completion": completion
                            }
                            messages.append(msg_dict)
            except discord.Forbidden:
                print(f'No access to channel {channel.name}')
            except Exception as e:
                print(f'Error in channel {channel.name}: {e}')

    # Write to JSONL file (oldest first)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for msg_dict in reversed(messages):
            f.write(json.dumps(msg_dict) + '\n')

    print(f'Exported {len(messages)} messages to {OUTPUT_FILE}')
    await bot.close()

bot.run(BOT_TOKEN)