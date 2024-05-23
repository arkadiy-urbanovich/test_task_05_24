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
    auth = HTTPBasicAuth('elastic', 'whatever')
    counter = count(1)

    while True:
        batch_no = next(counter)
        parts = ((
            json.dumps({"index": {"_index": "articles"}}),
            json.dumps({'title': title, 'link': link, 'text': text})
        ) for title, link, text in islice(data, BATCH_SIZE))
        body = ''.join('{}\n{}\n'.format(*part) for part in parts)
        if not body or batch_no > BATCHES:
            break
        print('Processing batch request', batch_no)
        stdout.flush()
        elastic_bulk_request(body, auth)


def elastic_bulk_request(body, auth, retry=0):
    try:
        resp = requests.post(
            url='https://elastic:9200/_bulk',
            data=body,
            auth=auth,
            verify=False,
            headers={'Content-Type': 'application/json'}
        )
        resp.raise_for_status()
    except requests.RequestException:
        if retry > 3:
            raise
        sleep(retry)
        elastic_bulk_request(body, auth, retry=retry + 1)


def main():
    get_abstracts()
    with open('./enwiki-latest-abstract.xml', 'rb') as fp:
        data = get_data(fp)
        add_data(data)


if __name__ == '__main__':
    main()
