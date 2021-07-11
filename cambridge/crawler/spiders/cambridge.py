import scrapy
from crawler.items import Page
from scrapy.linkextractors import LinkExtractor
from scrapy.loader import ItemLoader
from scrapy.spiders import CrawlSpider, Rule


class CambridgeSpider(CrawlSpider):
    name = 'cambridge'
    allowed_domains = ['dictionary.cambridge.org']

    url_start = 'https://dictionary.cambridge.org/us/browse/{0}/'
    url_dictionary = '/us/dictionary/{0}/'
    url_browse = '/us/browse/{0}/'

    def __init__(self, dictname='english', *args, **kwargs):
        self.dictname = dictname

        url = self.url_start.format(dictname)
        self.start_urls = [url]

        url_dictionary = self.url_dictionary.format(dictname)
        url_browse = self.url_browse.format(dictname)

        self.rules = (
            Rule(LinkExtractor(allow=url_dictionary),
                 callback='parse_item', follow=False),

            Rule(LinkExtractor(allow=url_browse), follow=True),
        )

        super(CambridgeSpider, self).__init__(*args, **kwargs)

    def parse_item(self, response):
        url = response.url
        il = ItemLoader(item=Page(), response=response)
        if not url.endswith('/'):
            il.add_value('url', url)
            il.add_value('html', response.body)

        return il.load_item()
