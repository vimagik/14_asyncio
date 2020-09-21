import pytest
import json
import os
from aiohttp import web

import main
from main import get_new_stories, save_html_page


async def hello(request):
    return web.Response(text='Hello', content_type='text/html')


async def get_new_stories_request(request):
    response = [1, 2, 4, 7]
    body = json.dumps(response)
    return web.Response(body=body, content_type='application/json')


async def get_items_request(request):
    response = {
        'id': '123',
        'url': 'url_string',
        'kids': ['123', '321'],
    }
    body = json.dumps(response).encode('utf-8')
    return web.Response(body=body, content_type='application/json')


async def get_comments_request(request):
    response = {
        'id': '111',
        'text': 'href="/"',
    }
    body = json.dumps(response).encode('utf-8')
    return web.Response(body=body, content_type='application/json')


def create_app(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', hello)
    app.router.add_route('GET', '/get_new_stories', get_new_stories_request)
    app.router.add_route('GET', '/123', get_items_request)
    app.router.add_route('GET', '/comments/321', get_comments_request)
    return app


@pytest.mark.parametrize(
    'test_value',
    [
        ({1, 2, 3}, {4, 7}),
        ({1, 3}, {2, 4, 7}),
        ({3}, {1, 2, 4, 7})
    ]
)
async def test_get_new_stories(test_client, test_value):
    old_stories, new_stories_match = test_value
    client = await test_client(create_app)
    new_stories = await get_new_stories('/get_new_stories', client, old_stories)
    assert new_stories == new_stories_match


async def test_get_item(test_client):
    client = await test_client(create_app)
    main.GET_ITEMS_URL = '/{}'
    story_id, url, comments = await main.get_item(client, '123')
    assert story_id == '123'
    assert url == 'url_string'
    assert comments == ['123', '321']


async def test_save_html_page_save_index(test_client):
    client = await test_client(create_app)
    await save_html_page('/', client, 123)
    new_path = os.path.join(main.OUTPUT_PATH, '123')
    new_file = os.path.join(new_path, 'index.html')
    assert os.path.exists(new_path)
    assert os.path.exists(new_file)
    os.remove(new_file)
    os.removedirs(new_path)


async def test_save_html_page_save_comment(test_client):
    client = await test_client(create_app)
    await save_html_page('/', client, 123, 321)
    new_path = os.path.join(main.OUTPUT_PATH, '123')
    new_file = os.path.join(new_path, '321.html')
    assert os.path.exists(new_path)
    assert os.path.exists(new_file)
    os.remove(new_file)
    os.removedirs(new_path)


async def test_save_all_pages_in_comment(test_client):
    client = await test_client(create_app)
    main.GET_ITEMS_URL = '/comments/{}'
    await main.save_all_pages_in_comment(client, 321, 123)
    new_path = os.path.join(main.OUTPUT_PATH, '123')
    new_file = os.path.join(new_path, '111.html')
    assert os.path.exists(new_path)
    assert os.path.exists(new_file)
    os.remove(new_file)
    os.removedirs(new_path)