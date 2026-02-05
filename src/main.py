import discord
from discord.ext import commands
from src.config import DISCORD_TOKEN
import sys

# Ensure src is in path if running as module or script
# but typically uv run python src/main.py works if configured right
# We will see.

class BattleMapsBot(commands.Bot):
    def __init__(self):
        # Enable message content intent to read messages for links
        intents = discord.Intents.default()
        intents.message_content = True
        
        # We don't use prefix commands, but the library requires a prefix argument.
        # We set it to a dummy value or a function that returns an empty list (if allowed, 
        # but empty strings/lists can be tricky). 
        # The cleanest way to "disable" it while satisfying the constructor is 
        # to use a prefix that nobody will likely use, or just minimal setup.
        # However, passing None or empty string might cause issues if not handled carefully.
        # We'll use a dummy prefix that effectively does nothing useful since we have no text commands.
        super().__init__(command_prefix=lambda _b, _m: [], intents=intents)

    async def setup_hook(self):

        # Load extensions
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
                
        # Syncing is now handled manually by the admin cog or on first run if needed
        # But for development it's often good to sync on startup. 
        # CAUTION: Global sync can be slow and rate-limited.
        # For now we will keep it for simplicity.
        await self.tree.sync()
        print("Commands synced")

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')

bot = BattleMapsBot()

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN not found in .env")
        print("Please create a .env file with DISCORD_TOKEN=your_token_here")
    else:
        bot.run(DISCORD_TOKEN)
