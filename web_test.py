from fastapi.testclient import TestClient
import pytest

import web as module


@pytest.fixture(scope='session')
def client():
    return TestClient(module.app)


def test_healthcheck(client):
    response = client.get('/health')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'details': None}


def test_add_article(client, mocker):
    async def fake_request(*args, **kwargs):
        resp = mocker.Mock()
        resp.status_code = 200
        resp.json.return_value = {
            '_index': 'articles',
            '_id': 'Bc1spY8BgXjrxMVve5OC',
            '_version': 1,
            '_seq_no': 93455,
            '_primary_term': 9,
            'found': True,
            '_source': {
                'title': 'title',
                'link': 'link',
                'text': 'text'
            }
        }
        return resp

    mocker.patch.object(module, 'requests', post=fake_request)

    response = client.post(
        '/articles',
        json={
            'title': 'title',
            'link': 'link',
            'text': 'text'
        }
    )

    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'details': 'Bc1spY8BgXjrxMVve5OC'}


def test_search_empty(mocker, client):
    async def fake_request(*args, **kwargs):
        resp = mocker.Mock()
        resp.status_code = 200
        resp.json.return_value = {
            'took': 58,
            'timed_out': False,
            '_shards': {},
            'hits': {
                'total': {
                    'value': 716,
                    'relation': 'eq'
                },
                'max_score': 9.408339,
                'hits': []
            }
        }
        return resp

    mocker.patch.object(module, 'requests', get=fake_request)

    response = client.get(
        '/articles?q=abc'
    )

    assert response.status_code == 200
    assert response.json() == []


def test_search(mocker, client):
    async def fake_request(*args, **kwargs):
        resp = mocker.Mock()
        resp.status_code = 200
        resp.json.return_value = {
            'took': 58,
            'timed_out': False,
            '_shards': {},
            'hits': {
                'total': {
                    'value': 716,
                    'relation': 'eq'
                },
                'max_score': 9.408339,
                'hits': [{
                    '_index': 'articles',
                    '_id': '4dhXpI8BCZQK_i-KmQom',
                    '_score': 9.408339,
                    '_ignored': [
                        'text.keyword'
                    ],
                    '_source': {
                        'title': 'Darwinism',
                        'link': 'https://en.wikipedia.org/wiki/Darwinism',
                        'text': 'Darwinism is a theory.'
                    }
                }, {
                    '_index': 'articles',
                    '_id': 'ut54pI8BpfYpsecocgX6',
                    '_score': 6.5218105,
                    '_source': {
                        'title': 'Parish church',
                        'link': 'https://en.wikipedia.org/wiki/Parish_church',
                        'text': 'The Church.'
                    }
                }]
            }
        }
        return resp

    mocker.patch.object(module, 'requests', get=fake_request)

    response = client.get(
        '/articles?q=abc'
    )

    assert response.status_code == 200
    assert response.json() == [{
        'link': 'https://en.wikipedia.org/wiki/Darwinism',
        'text': 'Darwinism is a theory.',
        'title': 'Darwinism',
    }, {
        'link': 'https://en.wikipedia.org/wiki/Parish_church',
        'text': 'The Church.',
        'title': 'Parish church',
    }]


def test_get_article(client, mocker):
    async def fake_request(*args, **kwargs):
        resp = mocker.Mock()
        resp.status_code = 200
        resp.json.return_value = {
            '_index': 'articles',
            '_id': 'abc',
            '_version': 1,
            '_seq_no': 93455,
            '_primary_term': 9,
            'found': True,
            '_source': {
                'title': 'Earle Herdan',
                'link': 'https://en.wikipedia.org/wiki/Earle_Herdan',
                'text': 'Earle Herdan is an American film editor.'
            }
        }
        return resp

    mocker.patch.object(module, 'requests', get=fake_request)

    response = client.get(
        '/articles/abc'
    )

    assert response.status_code == 200
    assert response.json() == {
        'link': 'https://en.wikipedia.org/wiki/Earle_Herdan',
        'text': 'Earle Herdan is an American film editor.',
        'title': 'Earle Herdan',
    }


def test_get_article_404(client, mocker):
    async def fake_request(*args, **kwargs):
        resp = mocker.Mock()
        resp.status_code = 404
        resp.json.return_value = {
            '_index': 'articles',
            '_id': 'abc',
            'found': False
        }
        return resp

    mocker.patch.object(module, 'requests', get=fake_request)

    response = client.get(
        '/articles/abc'
    )

    assert response.status_code == 404
    assert response.json() == {'status': 'not found'}
