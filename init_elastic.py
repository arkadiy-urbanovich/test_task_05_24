from itertools import islice, count
import json
import os
from sys import stdout
from time import sleep
from xml.etree import ElementTree

import requests
from requests.auth import HTTPBasicAuth
try:
    from requests.packages import urllib3
except ImportError:
    urllib3 = None

BATCH_SIZE = 100
MIN_SUMMARY_SIZE = 100
BATCHES = 10000
RETRY_TIMEOUTS = {
    1: 1,
    2: 5,
    3: 30
}
ELASTIC_AUTH = HTTPBasicAuth('elastic', 'whatever')


def get_abstracts():
    os.chdir('./downloads')
    if not os.path.exists('./enwiki-latest-abstract.xml.gz'):
        os.execv('wget', ('https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-abstract.xml.gz',))
    if not os.path.exists('./enwiki-latest-abstract.xml'):
        os.execv('gzip', ('-dk', './enwiki-latest-abstract.xml.gz'))


def get_data(fp):
    reading = False
    title = link = text = None
    parser = ElementTree.XMLParser(encoding='utf-8')
    for event, elem in ElementTree.iterparse(fp, events=('start', 'end'), parser=parser):
        if event == 'start' and elem.tag == 'doc':
            reading = True
            title = link = text = None
        elif reading and event == 'end':
            if elem.tag == 'title':
                title = str(elem.text).replace('Wikipedia: ', '')
            elif elem.tag == 'url':
                link = str(elem.text)
            elif elem.tag == 'abstract':
                text = str(elem.text)
            elif elem.tag == 'doc':
                if text and link and title and len(text) >= MIN_SUMMARY_SIZE:  # some abstracts are bad (like '}}}}}')
                    yield title, link, text
                reading = False


def add_data(data):
    if urllib3:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    counter = count(1)

    while True:
        batch_no = next(counter)
        parts = ((
            json.dumps({'index': {'_index': 'articles'}}),
            json.dumps({'title': title, 'link': link, 'text': text})
        ) for title, link, text in islice(data, BATCH_SIZE))
        body = ''.join('{}\n{}\n'.format(*part) for part in parts)
        if not body or batch_no > BATCHES:
            break
        print('Processing batch request', batch_no)
        stdout.flush()
        elastic_bulk_request(body)


def elastic_bulk_request(body, retry=0):
    try:
        resp = requests.post(
            url='https://elastic:9200/_bulk',
            data=body,
            auth=ELASTIC_AUTH,
            verify=False,
            headers={'Content-Type': 'application/json'}
        )
        resp.raise_for_status()
    except requests.RequestException:
        retry += 1
        if retry > 3:
            raise
        sleep(RETRY_TIMEOUTS[retry])
        elastic_bulk_request(body, retry=retry)


def create_es_index():
    body = {
        'mappings': {'properties': {
            'text': {'type': 'text'},
            'link': {'type': 'text'},
            'title': {'type': 'text'}
        }}
    }
    resp = requests.put(
        url='https://elastic:9200/articles',
        json=body,
        auth=ELASTIC_AUTH,
        verify=False,
    )
    resp.raise_for_status()


def main():
    get_abstracts()
    create_es_index()
    with open('./enwiki-latest-abstract.xml', 'rb') as fp:
        data = get_data(fp)
        add_data(data)


if __name__ == '__main__':
    main()
