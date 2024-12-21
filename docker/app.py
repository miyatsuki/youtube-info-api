import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any, Literal, Type, TypeVar

import openai
import requests
from pydantic import BaseModel


class PromptBaseModel(BaseModel, ABC):
    @classmethod
    @abstractmethod
    def template(cls) -> str:
        pass


T = TypeVar("T", bound=PromptBaseModel)


def parse_by_llm(s: str, structure: Type[T]):
    client = openai.Client(api_key=os.environ["OPENAI_API_KEY"])

    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-11-20",
        messages=[
            {
                "role": "system",
                "content": f"you are a Intelligent Data Parser, which turns unstructured data into following format.\n{structure.template()}",
            },
            {
                "role": "user",
                "content": f"次の入力を指定のフォーマットに変換してください。\n{s}",
            },
        ],
        response_format=structure,
    )

    assert response.choices[0].message.parsed
    return response.choices[0].message.parsed


class Video(PromptBaseModel):
    category: Literal["SONG", "GAME", "UNKNOWN"]
    type: Literal["VIDEO", "STREAM"]

    @classmethod
    def template(cls) -> str:
        return """
#### レスポンスフォーマット
```json
{
    "category": 動画のカテゴリ: "SONG" | "GAME" | "UNKNOWN" のいずれか,
    "type": 動画のタイプ: "VIDEO" | "STREAM" のいずれか
}
```

#### レスポンスの説明
- category: Literal["SONG", "GAME", "UNKNOWN"]
    動画のカテゴリ
    - SONG: 歌ってみた動画
    - GAME: ゲーム実況動画
    - UNKNOWN: それ以外
- type: Literal["VIDEO", "STREAM"]
    動画のタイプ
    - VIDEO: 動画
    - STREAM: 生放送
        """.strip()


def extract_video_id_from_url(url: str):
    pattern = r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})|(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})"
    match = re.match(pattern, url)

    if match:
        video_id = match.group(1) or match.group(2)
        return video_id
    else:
        return


def fetch_youtube_video_info(video_id: str):
    video_url = "https://www.googleapis.com/youtube/v3/videos"
    param = {
        "key": os.environ["YOUTUBE_DATA_API_TOKEN"],
        "id": video_id,
        "part": "snippet",
    }

    req = requests.get(video_url, params=param)
    result = req.json()
    return result


class SongInfo(PromptBaseModel):
    song_title: str
    singers: list[str]

    @classmethod
    def template(cls) -> str:
        return """
#### レスポンスフォーマット
```json
{
    "song_title": str 曲名,
    "singers": list[str] 歌手名,
}
```

#### レスポンスの説明
- song_title: str
    曲名
- singers: list[str]
    歌手名
        """.strip()


class CoverSongInfo(PromptBaseModel):
    song_title: str
    singers: list[str]
    is_cover: bool
    artists: list[str]
    original_url: str | None

    @classmethod
    def template(cls) -> str:
        return """
#### レスポンスフォーマット
```json
{
    "song_title": str 曲名,
    "singers": list[str] 歌手名,
    "is_cover": bool カバー曲かどうか,
    "artists": list[str] この曲の作者。is_coverがTrueの場合はカバー元の作者,
    "original_url": str | null オリジナル曲のURL。is_coverがTrueの場合はカバー元のURL、そうでない場合はnull
}
```

#### レスポンスの説明
- song_title: str
    曲名
- singers: list[str]
    歌手名
- is_cover: bool
    カバー曲かどうか
- artists: list[str]
    この曲の作者。is_coverがTrueの場合はカバー元の作者
    - ボカロ曲の場合はボカロPの名前
    - それ以外の場合はアーティスト名
- original_url: str | null
    オリジナル曲のURL。is_coverがTrueの場合はカバー元のURL、そうでない場合はnull
        """.strip()


class GameInfo(PromptBaseModel):
    """
    ゲーム実況動画の情報を格納するクラス

    Attributes:
    - game_title: str
        ゲームのタイトル
    """

    game_title: str | None

    @classmethod
    def template(cls) -> str:
        return """
#### レスポンスフォーマット
```json
{
    "game_title": str ゲームのタイトル
}
```

#### レスポンスの説明
- game_title: str
    ゲームのタイトル
        """.strip()


def lambda_handler(event, context):
    print(json.dumps(event))

    if "body" in event:
        data = json.loads(event["body"])
    else:
        data = event

    video = parse_by_llm(json.dumps(data), Video)
    ans: dict[str, Any] = {"category": video.category, "type": video.type}

    if video.category == "SONG":
        cover_song_info = parse_by_llm(json.dumps(data), CoverSongInfo)
        ans |= cover_song_info.model_dump()
        print(ans)

        if cover_song_info.is_cover and cover_song_info.original_url:
            youtube_id = extract_video_id_from_url(cover_song_info.original_url)
            if youtube_id:
                items = fetch_youtube_video_info(youtube_id)["items"]
                if len(items) > 0:
                    youtube_info = items[0]["snippet"]
                    original_video = parse_by_llm(json.dumps(youtube_info), Video)
                    if original_video.category == "SONG":
                        original_ans = parse_by_llm(json.dumps(youtube_info), SongInfo)
                        ans["song_title"] = original_ans.song_title
                        ans["artists"] = original_ans.singers
    elif video.category == "GAME":
        ans |= parse_by_llm(json.dumps(data), GameInfo)
    else:
        pass

    print(ans)
    return {"statusCode": 200, "body": ans}
