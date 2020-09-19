import aiohttp
import asyncio

URL = 'https://news.ycombinator.com/'


async def get_content(url, session):
    async with session.get(url) as response:
        data = await response.text()
        return data


async def main():
    async with aiohttp.ClientSession() as session:
        html = await get_content(URL, session)
        print(html)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
