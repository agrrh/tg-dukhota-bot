import hashlib
import json
import logging
import os
import redis
import datetime

from telegram import Update
from telegram.ext import ContextTypes

redis_host = os.environ.get("APP_REDIS_HOST", "127.0.0.1")
redis_port = int(os.environ.get("APP_REDIS_PORT", "6379"))

r = redis.Redis(host=redis_host, port=redis_port)


async def process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # logging.warning(update.to_dict())

    channel = update.message.chat.id
    channel_seek_depth = 100
    channel_seek_deep = True
    channel_history_limit = 1000
    content_min_length = 64

    channel_history_expire = datetime.timedelta(days=90)  # 3 months

    similar_weight_limit = 80

    # fingerprints

    update_message_dict = update.to_dict().get("message", {})

    fingerprint_id = {
        "forward_chat": update_message_dict.get("forward_from_chat", {}).get("id"),
        "forward_message_id": update_message_dict.get("forward_from_message_id"),
        "forward_username": update_message_dict.get("forward_from_chat", {}).get("username"),
        "this_chat": update_message_dict.get("chat", {}).get("id"),
        "this_message_id": update_message_dict.get("message_id"),
    }

    fingerprint_text = {
        "text": update_message_dict.get("text"),
        "caption": update_message_dict.get("caption"),
    }

    fingerprint_media = {
        "video": update_message_dict.get("video", {}).get("file_id"),
        "photo": list({photo.get("file_unique_id") for photo in update_message_dict.get("photo", [])}),
    }

    fingerprints = {
        "id": json.dumps(fingerprint_id),
        "text": json.dumps(fingerprint_text),
        "media": json.dumps(fingerprint_media),
    }

    fingerprints_md5 = hashlib.md5(json.dumps(fingerprints).encode("utf-8")).hexdigest()

    history_list = r.lrange(f"history:{channel}", 0, channel_seek_depth)
    logging.warning(fingerprints_md5)
    logging.warning(history_list)

    if fingerprints_md5.encode() in history_list:
        logging.warning(fingerprint_id)
        message_link = "https://t.me/c/{this_chat}/{this_message_id}".format(**candidate_id)
        await update.message.reply_text(f"🤓 {message_link}")
        return None

    elif channel_seek_deep:
        for candidate_md5 in history_list:
            similar_weight = 0

            candidate_md5 = candidate_md5.decode()

            candidate_id = r.hget(f"msg:{candidate_md5}", "id")
            candidate_id = json.loads(candidate_id.decode())

            message_link = "https://t.me/c/{this_chat}/{this_message_id}".format(**candidate_id)
            message_link = message_link.replace("/c/-100", "/c/")

            same_chat = candidate_id.get("this_chat") == fingerprint_id.get("this_chat")
            same_message_id = candidate_id.get("this_message_id") == fingerprint_id.get("this_message_id")

            if same_chat and same_message_id:
                similar_weight += 100

            if fingerprint_id.get("forward_chat"):
                same_forward_chat = candidate_id.get("forward_chat") == fingerprint_id.get("forward_chat")
                same_forward_message_id = candidate_id.get("forward_message_id") == fingerprint_id.get(
                    "forward_message_id"
                )

                if same_forward_chat and same_forward_message_id:
                    similar_weight += 100
                    message_link = "https://t.me/{forward_username}/{forward_message_id}".format(**candidate_id)

            candidate_text = r.hget(f"msg:{candidate_md5}", "text")
            candidate_text = json.loads(candidate_text.decode())

            if candidate_text.get("text") or candidate_text.get("caption"):
                len_content = max(
                    len(fingerprint_text.get("text") or ""),
                    len(fingerprint_text.get("caption") or ""),
                )
                if len_content < content_min_length:
                    continue

                same_text = candidate_text.get("text") == fingerprint_text.get("text")
                same_caption = candidate_text.get("caption") == fingerprint_text.get("caption")

                if same_text:
                    similar_weight += 45

                if same_caption:
                    similar_weight += 45

            candidate_media = r.hget(f"msg:{candidate_md5}", "media")
            candidate_media = json.loads(candidate_media.decode())

            if candidate_media.get("video") or candidate_media.get("photo"):
                same_video = candidate_media.get("video") == fingerprint_media.get("video")
                same_photo = candidate_media.get("photo") == fingerprint_media.get("photo")

                if same_video or same_photo:
                    similar_weight += 45

            # Result

            if similar_weight > 0:
                logging.warning(
                    f"similarity {fingerprints_md5} vs {candidate_md5}: {similar_weight} of {similar_weight_limit}"
                )

            if similar_weight > similar_weight_limit:
                await update.message.reply_text(f"🥸 {message_link}")
                return None

    r.hset(f"msg:{fingerprints_md5}", mapping=fingerprints)
    r.expire(f"msg:{fingerprints_md5}", channel_history_expire)

    r.lpush(f"history:{channel}", fingerprints_md5)
    r.ltrim(f"history:{channel}", 0, channel_history_limit)
