from dotenv import load_dotenv, find_dotenv
import os
import pprint
from pymongo import MongoClient
from datetime import datetime as dt
import urllib.parse

load_dotenv(find_dotenv())

password = urllib.parse.quote_plus(os.environ.get("MONGODB_PWD"))

connection_string = f"mongodb+srv://igorcalbo:{password}@tutorial.pweokxr.mongodb.net/?retryWrites=true&w=majority&appName=tutorial&authSource=admin"
client = MongoClient(connection_string)

dbs = client.list_database_names()
production = client.production

printer = pprint.PrettyPrinter()

### Schema Validation ###
def create_book_collection():
    book_validator = {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["title", "authors", "publish_date", "type", "copies"],
                "properties": {
                    "title": {
                        "bsonType": "string",
                        "description": "must be a string and is required"
                    },
                    "authors": {
                        "bsonType": "array",
                        "items": {
                            "bsonType": "objectId",
                            "description": "must be an objectid and is required"
                        }
                    },
                    "publish_date": {
                        "bsonType": "date",
                        "description": "must be a date and is required"
                    },
                    "type": {
                        "enum": ["Fiction", "Non-Fiction"],
                        "description": "can only be one of the enum values is required"
                    },
                    "copies": {
                        "bsonType": "int",
                        "minimum": 0,
                        "description": "must be a integer greater than 0 and is required"
                    },
                }
            }
        }

    try:
        production.create_collection("book")
    except Exception as e:
        print(e)

    production.command("collMod", "book", validator=book_validator)

def create_author_collection():
    author_validator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["first_name", "last_name", "date_of_birth"],
            "properties": {
                "first_name": {
                    "bsonType": "string",
                    "description": "must be a string and is required"
                },
                "last_name": {
                    "bsonType": "string",
                    "description": "must be a string and is required"
                },
                "date_of_birth": {
                    "bsonType": "date",
                    "description": "must be a date and is required"
                },
            }
        }
    }

    try: 
        production.create_collection("author")
    except Exception as e:
        print(e)

    production.command("collMod", "author", validator=author_validator)

### Bulk Insert ###
def create_data():
    authors = [
        {
            "first_name": "Igor",
            "last_name": "Calbo",
            "date_of_birth": dt(1998, 11, 10)
        },
        {
            "first_name": "George",
            "last_name": "Orwell",
            "date_of_birth": dt(1903, 6, 25)
        },
        {
            "first_name": "Herman",
            "last_name": "Melville",
            "date_of_birth": dt(1819, 8, 1)
        },
        {
            "first_name": "F. Scott",
            "last_name": "Fitzgerald",
            "date_of_birth": dt(1896, 9, 24)
        }
    ]
    author_collection = production.author
    authors = author_collection.insert_many(authors).inserted_ids

    books = [
        {
            "title": "MongoDB Advanced Tutorial",
            "authors": [authors[0]],
            "publish_date": dt.today(),
            "type": "Non-Fiction",
            "copies": 5
        },
        {
            "title": "Python for Dummies",
            "authors": [authors[1]],
            "publish_date": dt(2022, 1, 17),
            "type": "Non-Fiction",
            "copies": 5
        },
        {
            "title": "The Great Gatsby", 
            "authors": [authors[3]],
            "publish_date": dt(2014, 5, 23),
            "type": "Fiction",
            "copies": 5
        },
        {
            "title": "Moby Dick",
            "authors": [authors[2]],
            "publish_date": dt(1851, 9, 24),
            "type": "Fiction",
            "copies": 5
        }
    ]
    book_collection = production.book 
    book_collection.insert_many(books)

### Advanced Queries ###
def books_containing_a_func(): 
    books_containing_a = production.book.find({"title": {"$regex": "a{1}"}})
    printer.pprint(list(books_containing_a))

# join operation
def author_and_books_func():
    author_and_books = production.author.aggregate([{
        "$lookup": {
            "from": "book",
            "localField": "_id",
            "foreignField": "authors",
            "as": "books"
        }
    }])
    printer.pprint(list(author_and_books))

def author_book_count_func():
    author_book_count = production.author.aggregate([
        {
            "$lookup": {
                "from": "book",
                "localField": "_id",
                "foreignField": "authors",
                "as": "books"
            }
        },
        {
            "$addFields": {
                "total_books": {"$size": "$books"}
            }
        },
        {
            "$project": {"first_name": 1, "last_name": 1, "total_books": 1, "_id": 0}
        }
    ])
    printer.pprint(list(author_book_count))

def books_with_old_authors_func():
    books_with_old_authors = production.book.aggregate([
        {
            "$lookup": {
                "from": "author",
                "localField": "authors",
                "foreignField": "_id",
                "as": "authors"
            }
        },
        {
            "$set": {
                "authors": {
                    "$map": {
                        "input": "$authors",
                        "in": {
                            "age": {
                                "$dateDiff": {
                                    "startDate": "$$this.date_of_birth",
                                    "endDate": "$$NOW",
                                    "unit": "year"
                                }
                            },
                            "first_name": "$$this.first_name",
                            "last_name": "$$this.last_name",
                        }
                    }
                }
            }
        },
        {
            "$match": {
                "$and": [
                    {"authors.age": {"$gte": 50}},
                    {"authors.age": {"$lte": 150}},
                ]
            }
        },
        {
            "$sort": {
                "age": 1 # ascending order
            }
        }
    ])
    printer.pprint(list(books_with_old_authors))

### Pymongo Arrow Demo ###
import pyarrow
from pymongoarrow.api import Schema
from pymongoarrow.monkey import patch_all
import pymongoarrow as pma
from bson import ObjectId

patch_all()

author = Schema({"_id": ObjectId, "first_name": pyarrow.string(), "last_name": pyarrow.string(), "date_of_birth": dt})

df = production.author.find_pandas_all({}, schema=author)
arrow_table = production.author.find_arrow_all({}, schema=author)
ndarrays = production.author.find_numpy_all({}, schema=author)

print(ndarrays)
