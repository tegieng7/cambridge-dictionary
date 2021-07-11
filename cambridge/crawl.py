import logging
import pathlib

from scrapy.crawler import CrawlerProcess

import db
from crawler.spiders.cambridge import CambridgeSpider

logger = logging.getLogger(__name__)


def crawl_html(dictname):
    """Crawl html and store to mongodb.

    Args:
        dictname (str): Dictionary name eg. english, english-vietnamese
    """
    jobdir = pathlib.Path(__file__).parent.joinpath('job', dictname)

    # Create job directory
    jobdir.mkdir(parents=True, exist_ok=True)

    process = CrawlerProcess(settings={
        'MONGO_URI': db.URI,
        'MONGO_DATABASE': db.DBNAME,
        'JOBDIR': str(jobdir),
        'ITEM_PIPELINES': {
            'crawler.pipelines.MongoPipeline': 300,
        },
        'ROBOTSTXT_OBEY': False,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36 Edg/81.0.416.64'
    })

    # Start crawl
    process.crawl(CambridgeSpider, dictname=dictname, collection=db.HTML)
    process.start()
