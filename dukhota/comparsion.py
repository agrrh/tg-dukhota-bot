from pydantic import BaseModel
from typing import Optional, Final

import uuid
import difflib
import logging

from dukhota.message import Message


class Comparsion(BaseModel):
    uuid: Optional[str] = None

    message_a: Message
    message_b: Message

    media_ratio_limit: Final[float] = 0.66
    text_ratio_limit: Final[float] = 0.75
    text_ratio_forward_limit: Final[float] = 0.66
    text_ratio_media_limit: Final[float] = 0.33

    result: Optional[bool] = None

    def __init__(self, **kwargs) -> None:  # noqa: ANN003
        super().__init__(**kwargs)
        self.uuid = uuid.uuid4()
        self.result = self.check_equal()

    def check_equal(self) -> bool:  # noqa: CAC001, CCR001, CFQ004
        logging.info(f"Comparsion {self.uuid}: messages {self.message_a.fingerprint} vs {self.message_b.fingerprint}")

        logging.debug(self.message_a.dict(exclude_unset=True))
        logging.debug(self.message_b.dict(exclude_unset=True))

        if not (self.message_a.is_comparable() and self.message_b.is_comparable()):
            logging.error("Comparsion {self.uuid}: Could not check messages equality")
            return NotImplemented

        if self.message_a.fingerprint == self.message_b.fingerprint:
            logging.info("Comparsion {self.uuid}: Messages matched by fingerprint")
            return True

        same_message = (
            self.message_a.channel_id
            and self.message_a.channel_id == self.message_b.channel_id
            and self.message_a.message_id == self.message_b.message_id
        )

        if same_message:
            logging.info("Comparsion {self.uuid}: Messages matched as same ones")
            return True

        same_forwarded = (
            self.message_a.from_channel_id
            and self.message_a.from_channel_id == self.message_b.from_channel_id
            and self.message_a.from_message_id == self.message_b.from_message_id
        )

        if same_forwarded:
            logging.info("Comparsion {self.uuid}: Messages matched as same forwarded ones")
            return True

        compare_self = self.message_a.text or self.message_a.caption or ""
        compare_other = self.message_b.text or self.message_b.caption or ""

        if "" in (compare_self, compare_other):
            logging.debug(
                f"Comparsion {self.uuid}: "
                f"No text data for {self.message_a.fingerprint} vs {self.message_b.fingerprint}: "
                "setting same_text_ratio to 0.0",
            )
            same_text_ratio = 0.0
        else:
            same_text_ratio = difflib.SequenceMatcher(None, compare_self, compare_other).ratio()  # 0.00 to 1.00
            logging.debug(
                f"Comparsion {self.uuid}: "
                f"text ratio for {self.message_a.fingerprint} vs {self.message_b.fingerprint}: "
                f"{same_text_ratio}",
            )

        text_limit = self.text_ratio_forward_limit if self.message_a.is_forwarded else self.text_ratio_limit

        if self.message_a.significant_text and same_text_ratio > text_limit:
            logging.info(
                f"Comparsion {self.uuid}: Messages matched by same text ratio: {round(same_text_ratio, 2)}",
            )
            return True

        # same media

        if self.message_a.media_ids:
            same_media_list = list(set(self.message_a.media_ids) & set(self.message_b.media_ids))
            max_media_len = max(len(self.message_a.media_ids), len(self.message_b.media_ids))

            same_media_ratio = len(same_media_list) / max_media_len

            logging.debug(f"Comparsion {self.uuid}: same_media_ratio is {same_media_ratio}")

            if self.message_a.significant_text and same_text_ratio > self.text_ratio_media_limit:
                logging.info(
                    f"Comparsion {self.uuid}: "
                    "Messages matched by same text ratio with media presence: "
                    f"{round(same_media_ratio, 2)}, {round(same_text_ratio, 2)}",
                )
                return True

            if same_media_ratio >= self.media_ratio_limit:
                logging.info(
                    f"Comparsion {self.uuid}: "
                    "Messages matched by same media ratio: "
                    f"{round(same_media_ratio, 2)}, {round(same_text_ratio, 2)}",
                )
                return True

        return False
