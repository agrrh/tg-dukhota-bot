import os

from telegram.ext import ApplicationBuilder, MessageHandler, filters

from dukhota.dukhota import process

token = os.environ.get("APP_TG_TOKEN")
app = ApplicationBuilder().token(token).build()


to_process_filters = filters.TEXT | filters.PHOTO | filters.AUDIO | filters.VIDEO | filters.FORWARDED

app.add_handler(MessageHandler(to_process_filters, process))

app.run_polling()
