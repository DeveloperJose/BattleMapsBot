# BattleMaps Bot Setup

The bot is now configured and ready to run! Here's what needs to be done:

## Current Setup Status:
✅ Python dependencies installed via uv
✅ Redis container running in Docker
✅ Redis configuration set up
✅ Bot cogs configured in Redis

## Required Actions:

1. **Set your Discord Bot Token**
   - Get your token from the Discord Developer Portal
   - Update the token in Redis:
     ```bash
     uv run python -c "import redis; r = redis.Redis(host='localhost', port=6379, db=0); r.hset('{APP_NAME}:config:run', 'token', 'YOUR_BOT_TOKEN')"
     ```

2. **Choose which cogs to load**
   - Current cogs configured: admin, aw, c4, events, general, modlog, mod, poll, repl, selfroles, timer
   - Remove unwanted cogs from Redis:
     ```bash
     uv run python -c "import redis; r = redis.Redis(host='localhost', port=6379, db=0); r.delete('{APP_NAME}:config:initial_cogs')"
     ```

3. **Start the bot**
   ```bash
   uv run python main.py
   ```

## Redis Commands:
- View config: `uv run python -c "import redis; r = redis.Redis(host='localhost', port=6379, db=0); print(r.hgetall('{APP_NAME}:config:run'))"`
- View cogs: `uv run python -c "import redis; r = redis.Redis(host='localhost', port=6379, db=0); print(r.lrange('{APP_NAME}:config:initial_cogs', 0, -1))"`
- Reset token: `uv run python -c "import redis; r = redis.Redis(host='localhost', port=6379, db=0); r.hset('{APP_NAME}:config:run', 'token', 'YOUR_TOKEN_HERE')"`
