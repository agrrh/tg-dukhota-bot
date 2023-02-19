import datetime
import json
import logging
import os
import redis

from telegram import Update
from telegram.ext import ContextTypes

from dukhota.message import Message
from dukhota.helpers import tg_update_to_message

redis_host = os.environ.get("APP_REDIS_HOST", "127.0.0.1")
redis_port = int(os.environ.get("APP_REDIS_PORT", "6379"))

r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)


async def response(update: Update, ref_message: Message, emoji: str = "🤓") -> None:
    text = f"{emoji} https://t.me/c/{ref_message.chat_id}/{ref_message.message_id}"
    logging.debug(text)

    await update.message.reply_text(text)


async def process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:  # noqa: CCR001
    msg = tg_update_to_message(update)

    logging.warning(f"Processing message {msg.fingerprint}")
    logging.debug(msg)

    channel_seek_deep = True
    channel_seek_depth = 100
    channel_history_limit = 1000

    channel_history_expire = datetime.timedelta(days=90)  # 3 months

    logging.warning("Seek for message fingerprint in history")

    history_list = r.lrange(f"history:{msg.channel_id}", 0, channel_seek_depth)

    logging.debug(history_list)

    if msg.fingerprint in history_list:
        logging.warning("Found fingerprint in history")

        other_msg_data = json.loads(r.get(f"msg:{msg.fingerprint}"))

        # message is absent, remove from history
        if other_msg_data is None:
            r.lrem(f"history:{msg.channel_id}", 0, msg.fingerprint)

        other_msg = Message(**other_msg_data)
        logging.debug(other_msg)

        logging.warning(f"Refreshing {msg.fingerprint} TTL")
        r.expire(f"msg:{msg.fingerprint}", channel_history_expire)

        await response(update, other_msg)

    elif channel_seek_deep:
        logging.warning("Performing deep search")

        history_list = r.lrange(f"history:{msg.channel_id}", 0, channel_seek_depth)

        for other_msg_fingerprint in history_list:
            other_msg_data = json.loads(r.get(f"msg:{other_msg_fingerprint}"))
            other_msg = Message(**other_msg_data)

            if msg == other_msg:
                logging.warning("Found match during deep search")
                await response(update, other_msg, emoji="🥸")

                logging.warning(f"Saving message {msg.fingerprint} data")
                r.set(f"msg:{msg.fingerprint}", msg.json())
                r.expire(f"msg:{msg.fingerprint}", channel_history_expire)

                break

    logging.warning(f"Saving message {msg.fingerprint} to channel {msg.channel_id} history")
    r.lpush(f"history:{msg.channel_id}", msg.fingerprint)
    r.ltrim(f"history:{msg.channel_id}", 0, channel_history_limit)
