# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


import pymongo
# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


class MongoPipeline:

    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]

        self.collection = self.db[spider.collection]
        self.collection.create_index('url')
        self.collection.create_index('dictionary')

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        url = item.get('url')

        data = ItemAdapter(item).asdict()
        data.update({'dictionary': spider.dictname})

        item = {'url': url}
        self.collection.delete_many(item)

        self.collection.insert_one(data)

        return item
