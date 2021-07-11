import json
import logging
from pathlib import Path

import lxml.html

import db
import generate
from generate import get_all_inflection
from word import ErrorUndefinedWord, Word

logger = logging.getLogger(__name__)

DIR = Path(__file__).parent


def __get_attr(element):
    """Get attributes of lxml.html element.

    Args:
        element: lxml.html element

    Returns:
        dict: attributes of element
    """
    text = element.get('class', '')
    lst = [c for c in text.split(' ') if c]
    lst.sort()
    text = ' '.join(lst)

    attr = {
        'tag': element.tag,
        'class': text
    }

    return attr


def __get_route(root, element, lst_attr):
    """Get route from root to element.

    Args:
        root: lxml.html root
        element: lxml.html element
        lst_attr (list): list of attributes

    Returns:
        str: route
    """
    route = ''
    while element != root.getparent():
        attr = __get_attr(element)
        if attr not in lst_attr:
            lst_attr.append(attr)

        index = lst_attr.index(attr)
        route = '{0} {1}'.format(index, route).strip()

        element = element.getparent()

    return route


def __get_route_leafs(root, lst_attr):
    """Get all route to leaf.

    Args:
        root: lxml.html element
        lst_attr (lst): list of attributes

    Returns:
        list: list of route
    """
    def get_text(element):
        text = element.text_content()
        text = text.replace('\n', '').strip()
        return text

    lst_leaf = []

    for element in root.iter('*'):
        if len(element) > 0 or not get_text(element):
            continue

        route = __get_route(root, element, lst_attr)
        if route not in lst_leaf:
            lst_leaf.append(route)

    return lst_leaf


def __doc2word(doc):
    '''Convert document to word'''
    tree = lxml.html.fromstring(doc.get('html'))
    word = Word(tree)

    return word


def debug_collect_sample(dictname):
    """Analyze dictionary info then update to info collection

    Args:
        dictname (str): dictionary name eg. english, english-vietnamese
    """
    lst_doc = db.html_get_all(dictname)
    clt_info = db.clt_info

    lst_leaf = []
    lst_attr = []
    lst_url = []

    count = 0
    data = {}
    for doc in lst_doc:
        count += 1
        url = doc.get('url')
        logger.info('%s %s', count, url)

        root = lxml.html.fromstring(doc.get('html'))

        lst_leaf_new = __get_route_leafs(root, lst_attr)

        is_update = False
        for leaf in lst_leaf_new:
            if leaf not in lst_leaf:
                lst_leaf.append(leaf)
                is_update = True

        if is_update and url not in lst_url:
            lst_url.append(url)

        if is_update:
            clt_info.delete_many({
                'dictionary': dictname, 'document': 'sample'
            })

            lst_url.sort()
            lst_leaf.sort()

            data = {
                'dictionary': dictname,
                'document': 'sample',
                'urls': lst_url,
                'attributes': lst_attr,
                'leafs': lst_leaf
            }

            clt_info.insert_one(data)


def debug_check_layout(dictname):
    '''Check layout structure.'''
    dirpath = DIR.joinpath('result')

    lst_doc = db.html_get_sample(dictname)
    count = 0
    for doc in lst_doc:
        count += 1

        url = doc.get('url')
        wordname = url.split('/')[-1]

        logger.info('%s %s', count, url)

        word = __doc2word(doc)
        word.enable_debug(wordname, dirpath)

        word.collect()
        word.check_remain()


def debug_check_word(dictname, word):
    '''Check one word.'''
    dirpath = DIR.joinpath('result')

    doc = db.html_get_one(dictname, word)
    url = doc.get('url')
    name = url.split('/')[-1]

    logger.info(url)

    word = __doc2word(doc)
    word.enable_debug(name, dirpath)

    word.collect()
    word.check_remain()


def debug_export_info(dictname, dirname='info'):
    '''Export info collection to json file.'''
    dirpath = DIR.joinpath(dirname)
    dirpath.mkdir(parents=True, exist_ok=True)

    for doc in db.clt_info.find({'dictionary': dictname}):
        document = doc.get('document')

        logger.info('%s %s', dictname, document)

        del doc['_id']

        filename = '{0}_{1}.json'.format(dictname, document)
        filepath = dirpath.joinpath(filename)
        with open(filepath, 'w') as fp:
            json.dump(doc, fp, indent=4)


def parse_html(dictname):
    '''Collect data from dictionary.'''
    lst_doc = db.html_get_all(dictname)
    lst_err = []  # Error words
    lst_udn = []  # Undefined words
    count = 0
    for doc in lst_doc:
        count += 1
        try:
            url = doc.get('url')

            logger.info('%s %s', count, url)

            word = __doc2word(doc)
            data = word.collect()
            db.data_insert(data, dictname)

            word.check_remain()

        except ErrorUndefinedWord as e:
            logger.exception(e)
            lst_udn.append(url)

            # Update database
            db.info_update(dictname, 'undefineds', lst_udn)

        except Exception as e:
            logger.exception(e)
            lst_err.append(url)

            # Update database
            db.info_update(dictname, 'errors', lst_err)


def collect_words(dictname):
    '''Collect original words from data collection.'''
    lst_cid = []
    lst_title = []
    lst_inf = []
    list_word = []

    # Get list cid, title, inf
    count = 0
    for doc in db.clt_data.find({'dictionary': dictname}):
        count += 1

        title = doc.get('title', '')
        cid = doc.get('cid', '')

        logger.info('%s %s %s', count, title, cid)

        lst_cid.append(cid)
        lst_title.append(title)

        lst_inf_title = get_all_inflection(title)
        lst_inf_title.remove(title)
        lst_inf.extend(lst_inf_title)

    lst_cid = list(set(lst_cid))
    lst_title = list(set(lst_title))
    lst_inf = list(set(lst_inf))

    # Find original word
    count = 0
    for title in lst_title:
        count += 1

        logger.info('%s %s', count, title)

        if title not in lst_inf:
            list_word.append(title)

    list_word = list(set(list_word))

    # Sort list and add to database
    lst_cid.sort()
    lst_title.sort()
    list_word.sort()

    data = {
        'dictionary': dictname,
        'document': 'word',
        'cids': lst_cid,
        'titles': lst_title,
        'words': list_word
    }

    db.clt_info.delete_many({'dictionary': dictname, 'document': 'word'})
    db.clt_info.insert_one(data)


def generate_book(dictname):
    '''Generate book.'''
    generate.generate_ebook(dictname)
