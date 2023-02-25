import os
import logging

from telegram.ext import ApplicationBuilder, MessageHandler, filters

from dukhota.dukhota import process

LOGLEVEL = os.environ.get("LOGLEVEL", "WARNING").upper()
logging.basicConfig(level=LOGLEVEL)

for logging_module in ("hpack.hpack", "telegram._bot", "httpx._client"):
    logger = logging.getLogger(logging_module)
    logger.setLevel(logging.WARNING)

token = os.environ.get("APP_TG_TOKEN")
app = ApplicationBuilder().token(token).build()

to_process_filters = filters.TEXT | filters.PHOTO | filters.AUDIO | filters.VIDEO | filters.FORWARDED

app.add_handler(MessageHandler(to_process_filters, process))

app.run_polling()
