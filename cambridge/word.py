# -*- coding: utf-8 -*-

import json
import logging
import shutil
from collections import namedtuple
from pathlib import Path

import lxml.html
import yaml

logger = logging.getLogger(__name__)

DIR = Path(__file__).parent
LAYOUT = DIR.joinpath('word.yaml')


class ErrorUndefinedWord(Exception):
    pass


class ErrorNotFoundCategory(Exception):
    pass


class ErrorRemainText(Exception):
    pass


class ErrorEmptyResult(Exception):
    pass


class ErrorNotFoundBlock(Exception):
    def __init__(self, block):
        self.message = block
        super().__init__(self.message)


class ErrorMultipleSingleBlock(Exception):
    def __init__(self, block):
        self.message = block
        super().__init__(self.message)


class Word(object):

    def __init__(self, root, layout=LAYOUT):
        self.root = root

        with open(layout) as stream:
            data = yaml.safe_load(stream)
            self.__layout = namedtuple("Layout", data.keys())(*data.values())

        self.__css = self.__layout.css
        self.__cats = self.__find_cats()

        # Debug info
        self.__is_full = False
        self.__is_write = False
        self.__rst_dir = None
        self.__name = None

    def enable_debug(self, name, dirpath=None):
        '''Enable debug mode.

        Args:
            name (str): Word
            dirpath (Path, optional): Directory to write files. Defaults to None.
        '''
        self.__name = name
        self.__is_full = True
        if dirpath is not None:
            self.__is_write = True
            self.__rst_dir = Path(dirpath)
            self.__rst_dir.mkdir(parents=True, exist_ok=True)

    def collect(self):
        '''Collect data from etree base on structure in layout.'''
        data = []
        if self.__is_undefined() is True:
            raise ErrorUndefinedWord

        elif len(self.__cats) == 0:
            raise ErrorNotFoundCategory

        else:
            for category in self.__cats:
                self.__css = self.__layout.css
                self.__css.update(getattr(self.__layout, category))

                info = {'entry': self.__layout.entry}
                rst = self.__collect(self.root, info)

                if isinstance(rst['entry'], list) and rst:
                    data.extend(rst['entry'])

        # Write data in debug mode
        if self.__is_write is True:
            filepath = self.__rst_dir.joinpath('{0}.json'.format(self.__name))
            with open(filepath, 'w') as fp:
                json.dump(data, fp, indent=4)

            self.__write_html(self.root, '_remain')

        if data == []:
            raise ErrorEmptyResult

        return data

    def check_remain(self):
        '''Check remain content.'''
        # Clean bloat element
        self.__clean_bloat(self.root)

        # Clean ignore element
        self.__clean_ignore()

        # Clean empty element
        self.__clean_empty_element()

        if self.__is_write is True:
            self.__write_html(self.root, '_clean')

        text = self.root.text_content()
        if any(c.isalpha() for c in text):
            raise ErrorRemainText

    def __collect(self, tree, structure):
        '''Collect data from tree base on structure.'''
        result = {}
        for keyword, subture in structure.items():
            block = self.__find_block(tree, keyword)
            data = None

            if block is None:
                pass

            # New dict
            elif isinstance(subture, dict):
                if isinstance(block, list):
                    data = [self.__collect(b, subture) for b in block]
                else:
                    data = self.__collect(block, subture)

            else:
                if isinstance(block, list):
                    data = [self.__content(b, subture) for b in block]
                    [b.getparent().remove(b) for b in block]
                else:
                    data = self.__content(block, subture)
                    block.getparent().remove(block)

            # Not collect null data
            if self.__is_full is False and isinstance(data, list):
                data = [e for e in data if e]

            # Update result data:
            if self.__is_full is True or data:
                result.update({keyword: data})

        return result

    def __find_cats(self):
        '''Update css selector information.'''
        lst = [cat for cat in self.__layout.cssAll
               if self.root.cssselect(getattr(self.__layout, cat)['entry'])]

        return lst

    def __find_block(self, tree, keyword):
        '''Find block of key from tree.'''
        def is_valid(block, lst):
            valid = True
            if block is tree:
                valid = False
            else:
                for blk in lst:
                    if block is blk:
                        continue
                    elif block in blk.iter():
                        valid = False
                        break

            return valid

        slt = self.__css.get(keyword, 'UNDEFINED')
        lst_slt = slt if isinstance(slt, list) else [slt]

        lst_blk = []
        [lst_blk.extend(tree.cssselect(s)) for s in lst_slt]

        lst_valid = [b for b in lst_blk if is_valid(b, lst_blk)]

        size = self.__layout.size.get(keyword, '0+')
        if size[0] == '1' and len(lst_valid) == 0:
            self.__write_html(tree, '_block_0')
            raise ErrorNotFoundBlock(keyword)

        elif size[1] == '1' and len(lst_valid) > 1:
            self.__write_html(tree, '_block_1')
            raise ErrorMultipleSingleBlock(keyword)

        result = None
        if len(lst_valid) > 0:
            result = lst_valid[0] if size[1] == '1' else lst_valid

        return result

    def __is_undefined(self):
        '''Check word is undefined.'''
        undefined = False
        if len(self.__cats) == 0:
            for selector in self.__layout.undefined:
                if self.root.cssselect(selector):
                    undefined = True
                    break

        return undefined

    def __content(self, tree, method):
        '''Get content from eTree.'''
        if method == 'cid':
            text = tree.attrib.get('id')
        else:
            text = tree.text_content()

        return text

    def __write_html(self, tree, suffix=''):
        if self.__is_write is True:
            filename = "{0}{1}.html".format(self.__name, suffix)
            filepath = self.__rst_dir.joinpath(filename)
            html = lxml.html.tostring(tree)
            with open(filepath, 'wb') as fp:
                fp.write(html)

    def __clean_ignore(self):
        '''Remove block from ignore list.'''
        for selector in self.__layout.ignore:
            for block in self.root.cssselect(selector):
                block.getparent().remove(block)

    def __clean_bloat(self, root):
        '''Clean bloat block.'''
        selector = self.__layout.css.get('dictionary')
        for child in root:
            if child in root.cssselect(selector):
                continue
            elif child.cssselect(selector):
                self.__clean_bloat(child)
            else:
                root.remove(child)

    def __clean_empty_element(self):
        '''Clean empty element.'''
        def is_empty(element):
            text = element.text_content()
            empty = not any(c.isalpha() for c in text)
            return empty

        clean = True
        while clean:
            clean = False
            for element in self.root.iter():
                if is_empty(element) and element.getparent() is not None:
                    try:
                        element.getparent().remove(element)
                    except:
                        pass
