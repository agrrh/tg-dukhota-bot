import logging

from telegram import Update
from dukhota.message import Message


def tg_update_to_message(update: Update) -> Message:
    logging.debug(update.to_dict())

    update_message_dict = update.to_dict().get("message", {})

    channel_id = update_message_dict.get("chat", {}).get("id")
    message_id = update_message_dict.get("message_id")

    from_channel_id = update_message_dict.get("forward_from_chat", {}).get("id")
    from_message_id = update_message_dict.get("forward_from_message_id")

    text = update_message_dict.get("text")
    caption = update_message_dict.get("caption")

    video_id = update_message_dict.get("video", {}).get("file_unique_id")

    photo_ids = {photo.get("file_unique_id") for photo in update_message_dict.get("photo", [])}  # only unique ids

    media_ids = [video_id] + list(photo_ids)
    media_ids = list(filter(None, media_ids))  # remove empty

    return Message(
        channel_id=channel_id,
        message_id=message_id,
        from_channel_id=from_channel_id,
        from_message_id=from_message_id,
        text=text,
        caption=caption,
        media_ids=media_ids,
    )
