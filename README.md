# fbscraper

This python module lets you dump conversations from your Facebook account. It can also parse these dumped conversations for printing reports about messages, participants, files, pics, videos and links. A thread-approach mode lets even download it for you.

Compared to other solutions available, this is an almost automatic tool to dump and parse every conversation from your Facebook account.
I would like to thanks [RaghavSood](https://github.com/RaghavSood/FBMessageScraper) and [j6k4m8](https://github.com/j6k4m8/FBMessageScraper), my project is inspired from these two !

## Demo

Here is the video showing you the dumping and the parsing of a single conversation. Don't worry, the scraper may automatically scrapes everything, see Basic Usages below)

[![asciicast](https://asciinema.org/a/a9qozi9iqs36qz31trib5oxv6.png)](https://asciinema.org/a/a9qozi9iqs36qz31trib5oxv6)

## Basic Usages

the `fbscraper` is composed by two main tools, the `dumper` and the `parser`. There is a nice help option to let you known how to use them (`fbscraper -h` / `fbscraper dumper -h` / `fbscraper parser -h`).

The `--cookie` option is mandatory for both tools, this is all request headers and POST information that Facebook uses for authenticating yourself.

To get all this information, just open your browser and go inside the `Network tab` from the `Developers Tools` and navigate to any Facebook page. Select a request to a php file and copy the information in a file as follow:

![Request headers and POST data](/cookie.png)

Don't worry, you would just have to do this process once in a while when the cookie has expired.

By default, every information retrieved by both tools are saved inside `output` folder when you run the command. Both tools works very well together, see just below how to use them correctly !

### Dump them all...

Dump every bit of messages from every conversations of your Facebook account, process as follow:

`fb_scraper dumper -s 10000 -c request_data.txt`

### ... Then parse them all

Here is the basic command for parsing (using `dl` mode and retrieving any data type) all the conversations you have already dumped inside the `output` folder:

`fbscraper parser -m dl -i output/*/complete.json -c request_data.txt`

## Using the dumper

### Printing conversation metadata

First of all you should run this command in order to print some metadata about EVERY conversation attached to you:

`fbscraper dumper -c request_data.txt -meta`

It prints out conversation IDs, participants, type (group or user), status (inbox or archived).

### Dumping specific conversations based on their ID

Then you may want to dump specific conversations like this (`--size` / `-s` option lets you specify the chunk of messages retrieved by request):

`fb_scraper dumper -id id1 id2 id3 -s 10000 -c request_data.txt`

You will find inside the `output` folder, one folder for each conversation dumped with two files `complete.json` and  `complete.pretty.json` (more human-readable). These are all the information from a conversation, this is not very human readable data, therefore see how to parse it and retrieve meaning full data using the `Parser` tool.

## Using the parser

The parser uses the `--infile` option to specify which JSON conversation files you want to parse.

### Data types

The `--data` lets you specify which type of data you trying to retrieve from the parsing. You may specify one or many of the following: `messages  pictures gifs videos files links`. You may also just tell the dumper to try to retrieve any type using `all` (default option value).

### Report mode

Two modes you may choose using `--mode` option. `report` for only printing reports about conversations as follow:

```
Data report : 1552 messages, 18 pictures, 0 gifs, 0 videos, 1 files, 66 links parsed
```
You will find a file for each data types containing all information (links, messages...).

### Download mode

The `dl` mode, additionally to report, it also launches threads for downloading corresponding files (pictures, gifs, videos, non-media files).

`fbscraper parser -m dl -d all -i output/*/complete.json -c request_data.txt --threads=8`

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

`fbscraper` depends on two python modules:

* requests
* unidecode

### Installing

`fbscraper` is a python3 wheel package. Therefore you should run these commands from a python3 installation (which you can also set up with `virtualenv`). Here is the command for installing dependencies:


```
pip install -r requirements.txt
pip install dist/fbscraper-0.1-py3-none-any.whl
```

And you're ready to scrape them all !

## Acknowledgments

* The tool dumped even deleted or archived conversations. Once it has been upload to Facebook, it never truly disappear.
* Generated links  by Facebook have a short lifespan. If downloads can't be completed anymore, just use again the `dumper` to retrieve a new version of the conversation, and then use the `parser`.
* When parsing very large conversations, dumping messages can be time-consuming due to the formatting of a timestamp for each message. I tried myself with ~40k messages, it took like less than one minute for parsing and reporting everything.

## Futures improvements

* `Sphinx` documentation on the way. The whole code has been formatted to `PEP8` and `Sphinx Numpy Docstring` style.
* Add support for dumping and parsing Facebook pages.

## Contributing

Feel free to open a pull request at any bug encountered or improvement that you made.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
