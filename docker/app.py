import json
import os
import pathlib
import re
from typing import Literal

import openai
import requests
from miyatsuki_tools.llm_openai import parse_llm_output_json

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


def execute_openai(system_str: str, prompt: str, model: str = "gpt-3.5-turbo"):
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": system_str},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1024,
        temperature=0,  # 生成する応答の多様性,
    )

    return response.choices[0]["message"]["content"]


def classify_video_category(
    video_title: str, description: str
) -> Literal["SONG", "SINGING_STREAM", "GAME", "UNKNOWN"]:
    description = video_title + "\n" + description
    description = replace_urls(description, "[URL]")

    system_str = "You are a helpful assistant."
    prompt = f"""
説明文:
{description[:2000]}

=====

カテゴリを以下のように定義します
# GAME: ゲーム実況・ゲーム実況の生放送
# SINGING_STREAM: 歌枠
# SONG: 歌ってみた動画
# UNKNOWN: それ以外

この時、説明文の動画はどのカテゴリでしょうか？結果は以下のフォーマットで返してください。説明は不要です。
```json
{'{"video_type": category}'}
```
"""
    llm_result = execute_openai(system_str, prompt[1:-1])
    print(llm_result)
    result = parse_llm_output_json(llm_result, model="gpt-4")

    ans = result.get("video_type", "UNKNOWN").upper()
    if ans not in ["SONG", "SINGING_STREAM", "GAME", "UNKNOWN"]:
        ans = "UNKNOWN"

    return ans


def extract_song_info(video_title: str, description: str):
    system_str = (
        "You are a python simulator, which simulates the evaluation result of input"
    )
    prompt = f"""
```python
import json
from typing import List, Optional
import extract_song_title, extract_song_title, extract_singers, extract_original_artists, is_cover, extract_original_url

video_title = "{video_title}"
description = "{description[:2000]}"

answer = {{}}

# 動画のタイトルと概要欄から、曲名だけを抽出する。取得できない場合はNoneを返す
song_title: str = extract_song_title(video_title=video_title, description=description)
if song_title:
    answer["song_title"] = song_title

# 動画のタイトルと概要欄から、歌い手名を抽出する。取得できない場合は[]を返す
singers: List[str] = extract_singers(video_title=video_title, description=description)
if singers:
    answer["singers"] = singers

# 動画のタイトルと概要欄から、カバー曲かどうかを判定してフラグ追加
answer["is_cover"] = is_cover(video_title=video_title, description=description):

if answer["is_cover"]:
    # 動画のタイトルと概要欄から、オリジナルのアーティスト名を抽出する。取得できない場合は[]を返す
    artists: List[str] = extract_original_artists(video_title=video_title, description=description)
    if artists:
        answer["artists"] = artists

    # 動画の概要欄に、カバー元のURLが含まれていたらそれを返し、なければNoneを返す
    original_url: Optional[str] = extract_original_url(description=description)
    if original_url:
        answer["original_url"] = original_url

print(json.dumps(answer, indent=2, ensure_ascii=False)))
```
上記のコードの実行をシミュレートしてコンソール出力を予想してください。
実装がない箇所は関数名から挙動を仮定しながら進め、ImportErrorは無視してください。
説明は書かず、出力だけを記述してください。
"""
    llm_result = execute_openai(system_str, prompt[1:-1])
    result = parse_llm_output_json(llm_result)

    return result


def extract_original_song_info(video_title: str, description: str):
    system_str = (
        "You are a python simulator, which simulates the evaluation result of input"
    )
    prompt = f"""
```python
import json
from typing import List
import extract_song_title, extract_artists

video_title = "{video_title}"
description = "{description[:2000]}"

answer = {{}}

# 動画のタイトルと概要欄から、曲名だけを抽出する
song_title: str = extract_song_title(video_title=video_title, description=description)
answer["song_title"] = song_title

# 動画のタイトルと概要欄から、歌手名を抽出する
singers: List[str] = extract_singers(video_title=video_title, description=description)
answer["singers"] = singers

print(json.dumps(answer, indent=2, ensure_ascii=False)))
```
上記のコードの実行をシミュレートしてコンソール出力を予想してください。
実装がない箇所は関数名から挙動を仮定しながら進め、ImportErrorは無視してください
説明は書かず、出力だけを記述してください。
"""
    llm_result = execute_openai(system_str, prompt[1:-1])
    result = parse_llm_output_json(llm_result)

    return result


def extract_game_info(video_title: str, description: str):
    description = video_title + "\n" + description
    description = replace_urls(description, "[URL]")

    system_str = "You are a helpful assistant."
    prompt = f"""
コンテキスト:
{description[:2000]}

コンテキストはゲーム実況動画の説明文です。ゲームのタイトルを抽出してください。
結果は以下のフォーマットで返してください。説明は不要です
```json
{'{"game_title": answer}'}
```
"""
    llm_result = execute_openai(system_str, prompt[1:-1])
    result = parse_llm_output_json(llm_result, model="gpt-4")

    ans = result.get("game_title")

    if type(ans) == list:
        if len(ans) > 0:
            ans = ans[0]
        else:
            ans = None

    return ans


def lambda_handler(event, context):
    print(event)

    if "body" in event:
        data = json.loads(event["body"])
    else:
        data = event

    video_title = data["video_title"]
    description = data["description"]

    video_type = classify_video_category(video_title, description)
    ans = {"type": video_type}

    if video_type == "SONG":
        song_info = extract_song_info(video_title, description)
        ans |= song_info

        if song_info.get("is_cover") and song_info.get("original_url"):
            youtube_id = extract_video_id_from_url(song_info["original_url"])
            if youtube_id:
                items = fetch_youtube_video_info(youtube_id)["items"]
                if len(items) > 0:
                    youtube_info = items[0]["snippet"]
                    orignal_url_type = classify_video_category(
                        youtube_info["title"], youtube_info["description"]
                    )
                    if orignal_url_type == "SONG":
                        original_ans = extract_original_song_info(
                            youtube_info["title"], youtube_info["description"]
                        )
                        ans["song_title"] = original_ans["song_title"]
                        ans["artists"] = original_ans["singers"]

    elif video_type == "GAME":
        ans |= {
            "game_title": extract_game_info(video_title, description)
        }
    else:
        pass

    print(ans)
    return {"statusCode": 200, "body": ans}
