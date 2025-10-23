import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get sensitive data from .env
BOT_TOKEN = os.getenv('BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))  # Convert to int since IDs are numbers
USER_ID = int(os.getenv('USER_ID'))    # Convert to int
OUTPUT_FILE = 'user_messages.txt'

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

    messages = []
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).read_message_history:
            try:
                async for message in channel.history(limit=None):  # limit=None for all messages, but beware of rate limits
                    if message.author.id == USER_ID:
                        msg_str = f'{message.created_at} - {message.author.name}: {message.content}\n'
                        if message.attachments:
                            msg_str += f'Attachments: {", ".join([att.url for att in message.attachments])}\n'
                        messages.append(msg_str)
            except discord.Forbidden:
                print(f'No access to channel {channel.name}')
            except Exception as e:
                print(f'Error in channel {channel.name}: {e}')

    # Write to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for msg in reversed(messages):  # Reverse to have oldest first
            f.write(msg)

    print(f'Exported {len(messages)} messages to {OUTPUT_FILE}')
    await bot.close()

bot.run(BOT_TOKEN)