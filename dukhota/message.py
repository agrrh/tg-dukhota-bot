from pydantic import BaseModel
from typing import Optional, List

import hashlib


class Message(BaseModel):
    from_id: Optional[int]
    channel_id: Optional[int]
    message_id: Optional[int]

    from_channel_id: Optional[int]
    from_message_id: Optional[int]

    forward_from_id: Optional[int]

    text: Optional[str]
    caption: Optional[str]

    media_ids: Optional[List[str]]

    # hash of message contents
    fingerprint: Optional[str]

    significant_text: Optional[bool] = False
    is_forwarded: Optional[bool] = False

    # channel_id without "-100" prefix
    chat_id: Optional[int]

    def __init__(self, **kwargs) -> None:  # noqa: ANN003
        super().__init__(**kwargs)
        self.chat_id = self.__chat_id()
        self.fingerprint = self.__gen_fingerprint()
        self.significant_text = len(self.text or self.caption or "") > 64
        self.is_forwarded = self.__is_forwarded()

    def __chat_id(self) -> int:
        return int(str(self.channel_id).replace("-100", ""))

    def __gen_fingerprint(self) -> str:
        fingerprint_parts = [
            str(self.from_channel_id),
            str(self.from_message_id),
            self.text or self.caption or "",
            ",".join(self.media_ids),
        ]

        fingerprint = hashlib.sha256(";".join(fingerprint_parts).encode("utf-8")).hexdigest()

        return fingerprint[:16]

    def __is_forwarded(self) -> bool:
        return bool((self.from_channel_id and self.from_message_id) or self.forward_from_id)

    def is_comparable(self) -> bool:
        ids_present = self.channel_id and self.message_id
        significant_content = self.media_ids or self.significant_text

        forward_self = self.forward_from_id and self.forward_from_id == self.from_id

        return ids_present and significant_content and not forward_self
