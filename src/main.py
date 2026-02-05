import discord
from discord.ext import commands
from src.config import DISCORD_TOKEN
import sys

class BattleMapsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=lambda _b, _m: [], intents=intents)

    async def setup_hook(self):
        extensions = [
            "src.cogs.maps",
            "src.cogs.admin"
        ]

        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"Loaded extension: {ext}")
            except Exception as e:
                print(f"Failed to load extension {ext}: {e}")

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')


bot = BattleMapsBot()

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN not found in .env")
        print("Please create a .env file with DISCORD_TOKEN=your_token_here")
    else:
        print("Starting bot...")
        try:
            bot.run(DISCORD_TOKEN)
        except discord.errors.PrivilegedIntentsRequired:
            print("\n" + "="*60)
            print("CRITICAL ERROR: Privileged Intents are not enabled.")
            print("="*60)
            print("1. Go to the Discord Developer Portal: https://discord.com/developers/applications/")
            print("2. Select your application -> Bot")
            print("3. Scroll down to 'Privileged Gateway Intents'")
            print("4. Enable 'MESSAGE CONTENT INTENT'")
            print("5. Save Changes")
            print("="*60 + "\n")
            sys.exit(1)
        except Exception as e:
            print(f"Error starting bot: {e}")
            sys.exit(1)

