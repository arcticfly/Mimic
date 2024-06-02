import os
import asyncio
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.error import Forbidden, NetworkError

from audio_monitor import AudioMonitor

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

audio_monitor = AudioMonitor()


async def handle_update(bot: Bot, update_id: int) -> int:
    updates = await bot.get_updates(
        offset=update_id, timeout=10, allowed_updates=Update.ALL_TYPES
    )
    for update in updates:
        next_update_id = update.update_id + 1
        if update.message and update.message.text:
            print(f"Received message: {update.message.text}")
            if update.message.text == "on" and not audio_monitor.monitoring:
                asyncio.create_task(audio_monitor.start_monitoring())
            else:
                audio_monitor.stop_monitoring()
        return next_update_id
    return update_id


async def poll_updates():
    update_id = 0
    async with Bot(TOKEN) as bot:
        updates = await bot.get_updates(limit=1, timeout=10)
        if updates:
            update_id = updates[-1].update_id + 1

        print("Listening for messages...")
        while True:
            try:
                update_id = await handle_update(bot, update_id)
            except NetworkError:
                await asyncio.sleep(1)
            except Forbidden:
                update_id += 1


if __name__ == "__main__":
    try:
        asyncio.run(audio_monitor.start_monitoring())
        # asyncio.run(poll_updates())
    except KeyboardInterrupt:
        pass
    finally:
        print("\nStopped monitoring.")
