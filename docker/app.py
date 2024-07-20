import json
import os
import pathlib
import re
from typing import Literal

import marvin
import requests
from pydantic import BaseModel

marvin.settings.openai.chat.completions.model = "gpt-4o-mini"


class Video(BaseModel):
    """
    動画情報を格納するクラス

    Attributes:
    - category: Literal["SONG", "GAME", "UNKNOWN"]
        動画のカテゴリ
        - SONG: 歌ってみた動画
        - GAME: ゲーム実況動画
        - UNKNOWN: それ以外
    - type: Literal["VIDEO", "STREAM"]
        動画のタイプ
        - VIDEO: 動画
        - STREAM: 生放送
    """

    category: Literal["SONG", "GAME", "UNKNOWN"]
    type: Literal["VIDEO", "STREAM"]


base_dir = pathlib.Path(__file__).parent


def replace_urls(text, replacement=""):
    # URLを示す正規表現
    url_pattern = re.compile(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    )

    # 文字列中の全てのURLを置換
    return url_pattern.sub(replacement, text)


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


class SongInfo(BaseModel):
    """
    歌みた動画の情報を格納するクラス

    Attributes:
    - song_title: str
        曲名
    - singers: list[str]
        歌手名
        - ボカロ曲の場合はボカロPの名前
        - それ以外の場合はアーティスト名
    - is_cover: bool
        カバー曲かどうか
    """

    song_title: str | None
    singers: list[str] | None


class CoverSongInfo(SongInfo):
    """
    歌みた動画の情報を格納するクラス

    Attributes:
    - song_title: str
        曲名
    - singers: list[str]
        歌手名
        - ボカロ曲の場合はボカロPの名前
        - それ以外の場合はアーティスト名
    - is_cover: bool
        カバー曲かどうか
    - artists: list[str]
        この曲の作者。is_coverがTrueの場合はカバー元の作者
        - ボカロ曲の場合はボカロPの名前
        - それ以外の場合はアーティスト名
    - original_url: str
        オリジナル曲のURL。is_coverがTrueの場合はカバー元のURL、そうでない場合はこの動画のURL
    """

    is_cover: bool
    artists: list[str] | None
    original_url: str | None


class GameInfo(BaseModel):
    """
    ゲーム実況動画の情報を格納するクラス

    Attributes:
    - game_title: str
        ゲームのタイトル
    """

    game_title: str | None


def lambda_handler(event, context):
    print(event)

    if "body" in event:
        data = json.loads(event["body"])
    else:
        data = event

    video = marvin.cast(json.dumps(data), target=Video)
    ans = {"category": video.category, "type": video.type}

    if video.category == "SONG":
        song_info = marvin.cast(json.dumps(data), target=CoverSongInfo)
        ans |= song_info.model_dump()

        if song_info.is_cover and song_info.original_url:
            youtube_id = extract_video_id_from_url(song_info.original_url)
            if youtube_id:
                items = fetch_youtube_video_info(youtube_id)["items"]
                if len(items) > 0:
                    youtube_info = items[0]["snippet"]
                    original_video = marvin.cast(
                        json.dumps(youtube_info),
                        target=Video,
                    )
                    if original_video.category == "SONG":
                        original_ans = marvin.cast(
                            json.dumps(youtube_info), target=SongInfo
                        )
                        ans["song_title"] = original_ans.song_title
                        ans["artists"] = original_ans.singers

    elif video.category == "GAME":
        ans |= marvin.cast(json.dumps(data), target=GameInfo).model_dump()
    else:
        pass

    print(ans)
    return {"statusCode": 200, "body": ans}
