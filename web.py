from itertools import islice
from typing import Optional

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests_async as requests
from requests.auth import HTTPBasicAuth
import uvicorn

app = FastAPI()

ELASTIC_AUTH = HTTPBasicAuth('elastic', 'whatever')


class Article(BaseModel):
    text: str
    link: str
    title: str


class StatusResponse(BaseModel):
    status: str
    details: Optional[str] = None


@app.get('/health')
async def healthcheck() -> StatusResponse:
    return StatusResponse(status='ok')


@app.post('/articles')
async def add_article(article: Article, response: Response) -> StatusResponse:
    elastic_response = await requests.post(
        url='https://elastic:9200/articles/_doc',
        json=article.model_dump(),
        verify=False,
        auth=ELASTIC_AUTH
    )
    article_id = elastic_response.json()['_id']
    if elastic_response.status_code < 400:
        return StatusResponse(status='ok', details=article_id)

    response.status_code = response.status_code
    return StatusResponse(status='fail', details=elastic_response.text)


@app.get('/articles', response_model=list[Article], responses={500: {'model': StatusResponse}})
async def search(q: str, limit: int = 10):
    elastic_response = await requests.get(
        url='https://elastic:9200/articles/_search',
        auth=ELASTIC_AUTH,
        verify=False,
        json={'query': {'match': {'text': {'query': q, 'fuzziness': 'AUTO'}}}}
    )
    try:
        return [
            Article(**hit['_source'])
            for hit in islice(elastic_response.json()['hits']['hits'], limit)
        ]
    except KeyError:
        return JSONResponse(status_code=500, content={'status': 'fail', 'description': elastic_response.text})


@app.get(
    '/articles/{article_id}',
    response_model=Article,
    responses={404: {'model': StatusResponse}, 500: {'model': StatusResponse}}
)
async def get_article(article_id: str):
    elastic_response = await requests.get(
        url='https://elastic:9200/articles/_doc/' + article_id,
        auth=ELASTIC_AUTH,
        verify=False,
    )
    if elastic_response.status_code == 200:
        return Article(**elastic_response.json()['_source'])
    elif elastic_response.status_code == 404:
        return JSONResponse(status_code=404, content={'status': 'not found'})
    return JSONResponse(status_code=500, content={'status': 'fail', 'description': elastic_response.text})


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=80, reload=False)
