import argparse
import logging

import control
import crawl

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(lineno)s:%(name)-s %(levelname)-s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler()]
)


parser = argparse.ArgumentParser(description='Cambridge commands')
parser.add_argument('action', metavar='<action>',
                    choices=['crawl', 'parse', 'collect', 'generate', 'debug'])
parser.add_argument('dictname', metavar='<dictname>')
parser.add_argument('--option', metavar='<option>', default=None)

args = parser.parse_args()

if __name__ == "__main__":
    action = args.action
    dictname = args.dictname
    option = args.option

    # Crawl html and store to html collection
    if action == 'crawl':
        crawl.crawl_html(dictname)

    # Parse html to json and store to data collection
    elif action == 'parse':
        control.parse_html(dictname)

    # Collect list of word from data collection
    elif action == 'collect':
        control.collect_words(dictname)

    # Generate .mobi file
    elif action == 'generate':
        control.generate_book(dictname)

    # Debug get sample data for analyze
    elif action == 'debug':
        if option == 'sample':
            control.debug_collect_sample(dictname)
        elif option == 'layout':
            control.debug_check_layout(dictname)
        elif option == 'export':
            control.debug_export_info(dictname)
        else:
            control.debug_check_word(dictname, option)
