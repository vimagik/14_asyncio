import asyncio
import os
import re
from html import unescape
from time import monotonic
from asyncio import ProactorEventLoop

import aiohttp
from aiohttp import ClientSession
from aiohttp.client import ClientTimeout


TOP_STORIES_URL = 'https://hacker-news.firebaseio.com/v0/topstories.json?print=pretty'
GET_ITEMS_URL = 'https://hacker-news.firebaseio.com/v0/item/{}.json?print=pretty'
RUN_PERIOD = 600
OUTPUT_PATH = 'topstories'
CLIENT_TIMEOUT = 2.0
LIMIT_PER_HOST = 50


async def get_new_stories(url: str, session: ClientSession, old_stories: set) -> set:
    """Find new stories from top"""
    async with session.get(url) as response:
        data = await response.json()
        return set(data[:30]).difference(old_stories)


async def get_item(session: ClientSession, id_item: str) -> tuple:
    """Get id, url and comments from story"""
    async with session.get(GET_ITEMS_URL.format(id_item)) as response:
        data = await response.json()
        return data['id'], data.get('url'), data.get('kids')


def write_data(file_name: str, data: bytes) -> None:
    """Write downloaded data in file"""
    with open(file_name, 'wb') as file:
        file.write(data)


async def save_html_page(url: str, session: ClientSession, story_id: int, loop: ProactorEventLoop, comment_id: int = None) -> None:
    """Universal func for save stories and pages in comments"""
    new_path = os.path.join(OUTPUT_PATH, str(story_id))
    file_name = 'index.html' if not comment_id else f'{comment_id}.html'
    if not os.path.exists(new_path):
        os.mkdir(new_path)
    if url:
        try:
            async with session.get(url) as response:
                if response.content_type == 'text/html':
                    html = await response.read()
                    file_path = os.path.join(new_path, file_name)
                    await loop.run_in_executor(None, write_data, file_path, html)
        except (aiohttp.ClientConnectorError, aiohttp.ClientPayloadError, asyncio.TimeoutError):
            pass


async def save_all_pages_in_comment(session: ClientSession, comment_id: int, story_id: int, loop: ProactorEventLoop) -> None:
    """Find url in comments and download"""
    async with session.get(GET_ITEMS_URL.format(str(comment_id))) as response:
        data = await response.json()
        if data.get('deleted', False):
            return
        clean_data = unescape(data['text'])
        pattern = 'href=\"([^\"]+)'
        url_match = re.findall(pattern, clean_data)
        if url_match:
            for comment_url in url_match:
                await save_html_page(comment_url, session, story_id, loop, data['id'])


async def main() -> None:
    """Run with period of RUN_PERIOD, get and download new stories from TOP_STORIES_URL"""
    if not os.path.exists(OUTPUT_PATH):
        os.mkdir(OUTPUT_PATH)
    old_stories = set(int(story_id) for story_id in os.listdir(OUTPUT_PATH))
    try:
        while True:
            loop_for_write = asyncio.get_event_loop()
            start_iteration = monotonic()
            connector = aiohttp.TCPConnector(limit_per_host=LIMIT_PER_HOST)
            timeout = ClientTimeout(total=CLIENT_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                new_stories = await get_new_stories(TOP_STORIES_URL, session, old_stories)
                old_stories = old_stories.union(new_stories)
                if not new_stories:
                    break
                for get_func in asyncio.as_completed([get_item(session, story) for story in new_stories]):
                    item_id, item_url, comments = await get_func
                    await save_html_page(item_url, session, item_id, loop_for_write)
                    if not comments:
                        continue
                    for saved_comment in asyncio.as_completed([save_all_pages_in_comment(session, comment, item_id, loop_for_write) for comment in comments]):
                        await saved_comment
            duration = monotonic() - start_iteration
            print(f'{len(new_stories)} new stories downloaded by {duration} sec')
            await asyncio.sleep(RUN_PERIOD - duration)
    except KeyboardInterrupt:
        return


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
