# -*- coding: utf-8 -*-


import logging

import pymongo

logger = logging.getLogger(__name__)

URI = "mongodb://root:password@localhost:27017"
DBNAME = 'cambridge'
HTML = 'html'
INFO = 'info'
DATA = 'data'


client = pymongo.MongoClient(URI)
db = client[DBNAME]
clt_html = db[HTML]
clt_info = db[INFO]
clt_data = db[DATA]

# Create index
clt_data.create_index('dictionary')
clt_data.create_index('cid')
clt_data.create_index('title')


def html_get_one(dictname, word):
    '''Get one doc from html collection.'''
    url = 'https://dictionary.cambridge.org/us/dictionary/{dictname}/{word}'
    url = url.format(dictname=dictname, word=word)
    doc = clt_html.find_one({'dictionary': dictname, 'url': url})
    return doc


def html_get_all(dictname):
    '''Get all doc from html collection.'''
    cursor = clt_html.find({'dictionary': dictname})
    return cursor


def html_get_sample(dictname):
    '''Get all sample doc from html collection.'''
    filter = {'dictionary': dictname, 'document': 'sample'}
    lst_url = clt_info.find_one(filter).get('urls')
    filter.update({
        'url': {'$in': lst_url}
    })

    cursor = clt_html.find(filter)

    return cursor


def data_insert(data, dictname):
    '''Insert collect data to database'''
    for info in data:
        block = {'dictionary': dictname}
        block.update(info)
        filter = {
            'dictionary': dictname,
            'cid': info.get('cid'),
            'title': info.get('title')
        }
        clt_data.delete_many(filter)
        clt_data.insert_one(block)


def info_update(dictname, document, value):
    '''Update info collection.'''
    info = {
        'dictionary': dictname,
        'document': document
    }
    clt_info.delete_many(info)
    info.update({document: value})
    clt_info.insert_one(info)
