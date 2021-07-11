# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import lxml.html
import scrapy
from itemloaders.processors import MapCompose, TakeFirst


def get_article(html):
    tree = lxml.html.fromstring(html)
    lst = tree.cssselect('#page-content')
    if len(lst) == 1:
        html = lxml.html.tostring(lst[0])

    return html


class Page(scrapy.Item):
    url = scrapy.Field(
        output_processor=TakeFirst()
    )
    html = scrapy.Field(
        input_processor=MapCompose(get_article),
        output_processor=TakeFirst()
    )
