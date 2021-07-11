import itertools
import logging
import shutil
from datetime import date
from pathlib import Path
from subprocess import PIPE, STDOUT, Popen

import yaml
from lemminflect import getAllInflections

import db


class ErrorEmptyDefinition(Exception):
    pass


logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(lineno)s:%(name)-s %(levelname)-s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)

DIR = Path(__file__).parent

DIR_TMP = DIR.joinpath('dictionary')
DIR_OUT = DIR.joinpath('output')

KINDLEGEN = DIR.joinpath('kindlegen.exe')
DOWNLOAD = DIR.parent.joinpath('download')

TMP_FILES = ['index.html', 'index.opf', 'info.html']

PRIORITY = {
    'cald4': 1,
    'cald4-us': 2,
    'cbed': 3,
    'cacd': 4
}


def get_word_inflection(word: str) -> list:
    '''Get all inflections of word by using lemminflect library.

    Args:
        word (str): word

    Returns:
        list: list of inflections
    '''
    lst_inf = [word]

    lst_wait = [word]
    lst_done = []
    while lst_wait:
        word_next = lst_wait[-1]
        lst_wait.pop(-1)

        if word_next in lst_done:
            continue

        lst = []
        [lst.extend(list(v)) for _, v in getAllInflections(word_next).items()]
        lst_done.append(word_next)

        lst_inf.extend(lst)
        lst_wait.extend(lst)
        lst_wait = list(set(lst_wait))

    lst_inf = list(set(lst_inf))

    return lst_inf


def get_all_inflection(pharse: str) -> list:
    '''Get all inflections of word or phase'''
    lst_word_inf = [get_word_inflection(word)
                    for word in pharse.split(' ') if word]
    lst_combination = list(itertools.product(*lst_word_inf))
    lst_phase_inf = [' '.join(l) for l in lst_combination]

    if pharse in lst_phase_inf:
        lst_phase_inf.remove(pharse)
    lst_phase_inf.insert(0, pharse)

    return lst_phase_inf


def __generate_entry(data: dict) -> str:
    '''Generate entry block of word.

    Args:
        data (dict): data of word. Keywords: title, ipa, pos, def

    Returns:
        str: entry block
    '''
    entry = '''
        <idx:entry name="english" scriptable="yes" spell="yes">
            <idx:orth value="{title}"><b>{title}</b>
                <idx:infl>{lst_iform}</idx:infl>
            </idx:orth>
            {dash_br} {ipa} {dash} {pos}
            {definition}
        </idx:entry>
        <mbp:pagebreak />
    '''
    str_iform = '<idx:iform value="{form}" />'

    lst_iform = ''
    for form in data.get('lst_inf', []):
        iform = str_iform
        iform = iform.format(form=form)

        lst_iform += iform

    data.update({'lst_iform': lst_iform})
    entry = entry.format(**data)

    return entry


def __get_ipa_data(word: str) -> dict:
    '''Collect ipa info from multiple dictionary in db.

    Args:
        word (str): word

    Returns:
        dict: ipa data {pos: [us, uk]}
    '''
    filter = {'title': word}
    data = {}
    for doc in db.clt_data.find(filter):
        pos = doc.get('pos', [None])[0]
        lst = data.get(pos, [None, None])
        if doc.get('ipaUS') and not lst[0]:
            lst[0] = doc.get('ipaUS')[0]
            data.update({pos: lst})

        if doc.get('ipaUK') and not lst[1]:
            lst[1] = doc.get('ipaUK')[0]
            data.update({pos: lst})

    for pos, ipa in data.items():
        if ipa[0] is None and ipa[1]:
            ipa[0] = ipa[1]
        if ipa[0] and ipa[1] is None:
            ipa[1] = ipa[0]

        data.update({pos: ipa})

    return data


def __get_block_entry(doc: dict) -> dict:
    '''Process doc to create data to generate entry.

    Args:
        doc (dict): block data get from database

    Returns:
        dict: data. Keywords: title, ipa, pos, def
    '''
    del doc['_id']

    # Update cid
    cid = doc.get('cid', '-1')
    cid = '-'.join(cid.split('-')[:-1])

    # Get ipa & pos
    ipa = doc.get('ipa')
    pos = doc.get('pos')
    dash = '-' if ipa and pos else ''
    dash_br = '<br>' if ipa or pos else ''

    ipa = '/{0}/'.format(ipa) if ipa else ''
    pos = '<i>{0}</i>'.format(pos) if pos else ''

    # Get def
    text = ''
    for sense in doc.get('posSense', []):
        text_sense = ''
        guide = ' '.join(sense.get('guideWord', []))
        if guide:
            guide = '<br>{0}'.format(guide)
            text_sense += guide

        title = sense.get('pvTitle')
        if title:
            title = '<br>{0}'.format(title)
            text_sense += title
            text_sense += title

        # defBlock
        text_def = ''
        count = 0
        for block in sense.get('defBlock', []):
            count += 1
            prefix = '&#9726; '

            define = ' '.join(block.get('define', []))
            if define:
                define = '<br>{0}{1}'.format(prefix, define)
                text_def += define

            translation = ' '.join(block.get('trans', []))
            if translation:
                translation = '<br><i>{0}</i>'.format(translation)
                text_def += translation

            examp = block.get('examp', [])
            bull = '&nbsp;&nbsp; &bull;'
            lst = ['<i>{0} {1}</i>'.format(bull, eg)
                   for eg in examp]
            if lst:
                examp = '<br>' + '<br>'.join(lst)
                text_def += examp

        # Append block
        text_sense = text_sense + text_def if text_def else ''

        text += text_sense

    if not text:
        raise ErrorEmptyDefinition

    text += '<br>'

    # Update document
    doc.update({
        'cid': cid,
        'ipa': ipa,
        'pos': pos,
        'dash': dash,
        'dash_br': dash_br,
        'definition': text
    })

    return doc


def __get_be_removed_index(lst_info):
    '''Clean block in the case multiple dictionary definition for word.'''
    lst_info = sorted(lst_info, key=lambda x: (x[0], x[1], x[2]))
    lst_remove = []
    previous = None
    for item in lst_info:
        if previous is None or item[0] != previous[0]:
            previous = item
            continue
        elif item[0] == previous[0] and item[1] != previous[1] and item[1] != 'zzz':
            previous = item
            continue
        else:
            lst_remove.append(item[-1])

    return lst_remove


def __get_lst_block(dictname: str, word: str) -> list:
    '''Get list of defination block.'''
    lst_title = get_all_inflection(word)

    lst_block = []
    lst_block_cid = []
    filter = {'dictionary': dictname, 'title': {'$in': lst_title}}
    for doc in db.clt_data.find(filter):
        data_ipa = __get_ipa_data(doc.get('title'))

        pos = doc.get('pos', [None])[0]

        lst_ipa = data_ipa.get(pos, [None, None])
        if lst_ipa[0] is None and data_ipa:
            lst_ipa = list(data_ipa.values())[0]

        doc.update({
            'pos': pos,
            'ipa': lst_ipa[0],
            'lst_inf': lst_title
        })

        try:
            block = __get_block_entry(doc)
            lst_block.append(block)

            cid_number = PRIORITY.get(block.get('cid'), 1)
            pos = pos if pos else 'zzz'
            lst_block_cid.append([
                block.get('title'), pos, cid_number, len(lst_block) - 1
            ])
        except:
            pass

    # Remove duplicate blocks
    for index in __get_be_removed_index(lst_block_cid):
        lst_block[index] = None

    lst_block_rst = [b for b in lst_block if b]

    return lst_block_rst


def __generate_html(info, dir_rst, lst_page):
    '''Generate html files.'''
    file_html = DIR_TMP.joinpath('index.html')
    with open(file_html) as fp:
        html_tmp = fp.read()

    lst_item = ''
    lst_itemref = ''

    for index in range(len(lst_page)):
        info.update({'lst_entry': lst_page[index]})
        html_text = html_tmp.format(**info)

        filename = '{0}.html'.format(index)
        filepath = dir_rst.joinpath(filename)
        with open(filepath, 'w', encoding='utf-8') as fp:
            fp.write(html_text)

        item = '<item id="{0}" href="{0}.html" media-type="application/xhtml+xml" />'
        item = item.format(index)
        lst_item += item

        itemref = '<itemref idref="{0}" />'
        itemref = itemref.format(index)
        lst_itemref += itemref

        info.update({
            'lst_item': lst_item,
            'lst_itemref': lst_itemref
        })

    return info


def __generate_directory(dictname: str, lst_page: list) -> None:
    '''Generate dictionary directory from template.

    Args:
        dictname (str): name of dictionary
        lst_page (list): list of page

    Returns:
        str: path to opf file
    '''
    dir_rst = DIR_OUT.joinpath(dictname)
    if dir_rst.exists():
        shutil.rmtree(dir_rst)
    dir_rst.mkdir(parents=True, exist_ok=True)

    # Load config data
    filepath = DIR_TMP.joinpath('{0}.yaml'.format(dictname))
    with open(filepath) as stream:
        info = yaml.safe_load(stream)

    info.update({'generateDay': date.today()})

    # Generate html
    info = __generate_html(info, dir_rst, lst_page)

    # Copy template files
    for filename in TMP_FILES:
        if filename in ['index.html']:
            continue

        filepath = DIR_TMP.joinpath(filename)
        with open(filepath) as fp:
            text = fp.read()

        text = text.format(**info)

        # Write to file
        filepath = dir_rst.joinpath(filename)
        with open(filepath, 'w', encoding='utf-8') as fp:
            fp.write(text)

    # Copy cover
    cover = '{0}.jpg'.format(dictname)
    src = DIR_TMP.joinpath(cover)
    target = dir_rst.joinpath(cover)
    shutil.copy(src, target)

    file_opf = dir_rst.joinpath('index.opf')

    return file_opf


def generate_ebook(dictname):
    # Get list of word
    filter = {'dictionary': dictname, 'document': 'word'}
    info = db.clt_info.find_one(filter)
    lst_word = [w.strip() for w in info.get('words', [])]

    lst_page = []
    text_page = ''
    prev = '0'
    count = 0
    for word in lst_word:
        char = word[0].lower() if word[0].isalpha() else '0'
        if char != prev:
            if text_page:
                lst_page.append(text_page)

            prev = char
            text_page = ''

        count += 1
        logger.info('%s %s', count, word)
        for block in __get_lst_block(dictname, word):
            str_block = __generate_entry(block)
            text_page += str_block

    # Append last page
    lst_page.append(text_page)

    file_opf = __generate_directory(dictname, lst_page)

    # Generate .mobi
    DOWNLOAD.mkdir(parents=True, exist_ok=True)
    filename = 'cambridge-{0}.mobi'.format(dictname)
    file_mobi = DOWNLOAD.joinpath(filename)

    args = [KINDLEGEN, file_opf, '-c2', '-verbose',
            '-dont_append_source', '-o', filename]

    with Popen(args, stdout=PIPE, stderr=STDOUT, text=True, bufsize=1) as p:
        for buf in p.stdout:
            string = str(buf).strip()
            if string:
                logger.info(string)

    # Copy file to download directory
    src = Path(file_opf).parent.joinpath(filename)
    shutil.copy(src, file_mobi)
