#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""parse module.

This module is used for parsing a FB JSON conversation and retrieve
different data

Examples
--------
>>> from fbscraper.parser import FBParser
>>> fb_parser = FBParser(['complete.json', 'complete2.json'], 'dl', 'pictures')
>>> fb_parser.parse()

"""
import json
import os
import re
from datetime import datetime
from urllib import parse

import requests
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor
from unidecode import unidecode

from fbscraper.dumper import FBDumper
from fbscraper.lib import FBDataTypes, FBParserMode, PrintLoading, \
                          OUTPUT_DEFAULT_FOLDER, \
                          format_convers_metadata


class FBParser(object):
    """Class for parsing Facebook JSON conversations.

    Attributes
    ----------
    summary_report_fmt : str
        Format string used for displaying a summary of all data reports.
        May be changed to suit your need.
    message_fmt : str
        Format string used for storing messages.
        May be changed to suit your need.

    Parameters
    ----------
    user_raw_data: dict
        User raw POST data used for getting conversations metadata
        (using `FBDumper`).
    json_msgs : dict, optional
        JSON conversation
    infile_json : str, optional
        Filepath from where to load the JSON conversation.
    mode : FBParserMode, optional
        Mode to use. The default is `FBParserMode.REPORT`.
    data : FBDataTypes, optional
        Data types to retrieve. The default is `FBDataTypes.ALL`.
    threads : int, optional
        Number of threads to use for DL mode. The default is 4.
    output : str, optional
       Folder output where to save data. May be common between
       conversations dumped or parsed.

    Raises
    ------
    ValueError
        When both a `json_msgs` or a `infile_json` are provided.

        When the number of `threads` is inferior or equal to 0.

    See Also
    --------
    FBDumper :Used for getting all conversations
        metadata for the specific user (related to `user_raw_data` cookie).

    Notes
    -----
    Conversations parsed must have their metadata dumpable. To do so,
    try to parse only conversations that is related to `user_raw_data`
    parameter cookie.

    """

    summary_report_fmt = "[+]     - Data report : {} messages, {} pictures, " \
                         "{} gifs, {} videos, {} files, {} links parsed"

    message_fmt = "Message body: {} - attachments {{{}}} - sent by: '{}' " \
                  "({}) - the {}\n"

    _url_username_api = "https://graph.facebook.com/{}?access_token={}"
    _url_username = "https://facebook.com/profile.php?id="
    _regex_username = r'<title id="pageTitle">(.*?)</title>'
    _bad_page_title = "Page introuvable | Facebook"
    _action_type_user_msg = "ma-type:user-generated-message"

    def __init__(self, user_raw_data, json_msgs=None, infile_json=None,
                 mode=FBParserMode.REPORT, data=FBDataTypes.ALL,
                 threads=4, output=OUTPUT_DEFAULT_FOLDER):
        """__init__ method."""
        if bool(json_msgs) ^ bool(infile_json):
            if json_msgs:
                self.json_msgs = json_msgs
            else:
                self.infile_json = infile_json
        else:
            raise ValueError('You should either provide a JSON dict'
                             '`json_msgs` or a filepath as `infile_json`.')

        self.mode = mode
        self.data = data
        self.output = os.path.join(output, '')
        os.makedirs(self.output, exist_ok=True)

        if threads <= 0:
            raise ValueError('Thread parameter must be superrior to 0. '
                             'Value : {}'.format(threads))
        self.threads = threads

        fb_dumper = FBDumper("", user_raw_data, chunk_size=2000, output=output)

        self.convers = fb_dumper.convers
        self.participants = fb_dumper.participants

        if self.mode == FBParserMode.DL:
            self.executor = ThreadPoolExecutor(max_workers=threads)
            self.futures = {}
        else:
            self.executor = None

    def init_parser_for_next(self, infile_json):
        """Init the instance attributes for parsing the `infile_json` file.

        Parameters
        ----------
        infile_json : str
            Filepath from where to load the JSON conversation.

        """
        with open(infile_json, 'r') as f:
            self.json_msgs = json.load(f)
        self.convers_id = self.get_conversation_id()
        self.output_convers = os.path.join(self.output, self.convers_id + " - "
                                           + unidecode(self.convers[
                                               self.convers_id]
                                               ["name"]),
                                           '')
        os.makedirs(self.output_convers, exist_ok=True)
        if self.mode == FBParserMode.DL:
            for e in FBDataTypes:
                if (e != FBDataTypes.ALL and e != FBDataTypes.MESSAGES
                        and e != FBDataTypes.LINKS):
                    os.makedirs(self.output_convers + e.value, exist_ok=True)

        self.msgs = ""
        self.pics = ""
        self.gifs = ""
        self.videos = ""
        self.files = ""
        self.links = ""
        self.cnt_msgs = 0
        self.cnt_pics = 0
        self.cnt_gifs = 0
        self.cnt_videos = 0
        self.cnt_files = 0
        self.cnt_links = 0
        self.quit = False
        self.futures = {}

    def get_conversation_id(self):
        """Extract conversation id from `self.json_msgs`.

        Returns
        -------
        str
            Return the conversation id. If any found, return None.

        Raises
        ------
        ValueError
            JSON data seems malformed, can not access specific key.

        """
        user = "other_user_fbid"
        group = "thread_fbid"
        if self.json_msgs[0][user] is not None:
            return self.json_msgs[0][user]

        if self.json_msgs[0][group] is not None:
            return self.json_msgs[0][group]

        raise ValueError("JSON data seems malformed. Can't retrieve the"
                         "conversation ID. Verify your JSON input file."
                         "If the file seems fine, please open an issue on"
                         "Github.")

    def common_checks(self, msg):
        """Common checks perform on a message.

        Parameters
        ----------
        msg : dict
            JSON Formatted Facebook message to check

        Returns
        -------
        bool
            True if checks are successful, False otherwise.

        Notes
        -----
        A message is considered as a message if it is generated by a user.
        Logs messages such as conversation renamed won't be reported.

        """
        if msg["action_type"] == self._action_type_user_msg:
            return True
        else:
            return False

    def check_and_get_msg(self, msg):
        """Check if msg is containing a message and stored it in self.msgs.

        Parameters
        ----------
        msg : dict
            JSON Formatted Facebook message.

        """
        attachments = ''.join([str(a["name"])
                              + " " for a in msg["attachments"]
                              if a["attach_type"] != "error"])[:-1]

        fbid = msg["author"][5:]
        username = self.participants[fbid] if fbid in self.participants else ""
        self.msgs += self.message_fmt.format(repr(msg["body"]), attachments,
                                             username, fbid,
                                             datetime.fromtimestamp(
                                                msg["timestamp"] / 1000)
                                             .strftime('%Y-%m-%d %H:%M:%S'))

        self.cnt_msgs += 1

    def check_and_get_pics(self, msg):
        """Check if msg is containing pictures and stored it in self.pics.

        Parameters
        ----------
        msg : dict
            JSON Formatted Facebook message.

        """
        for attachment in msg["attachments"]:
            if (attachment["attach_type"] == "photo" and
                    attachment["preview_url"] is not None):

                if (self.mode == FBParserMode.REPORT
                        or self.mode == FBParserMode.DL):
                    self.pics += attachment["preview_url"] + "\n"

                if self.mode == FBParserMode.DL:
                    dl_path = self.output_convers \
                        + FBDataTypes.PICTURES.value \
                        + os.sep + attachment["name"]
                    self.futures[self.executor.
                                 submit(self.dl_file,
                                        attachment["preview_url"],
                                        dl_path)] = attachment["preview_url"]

                self.cnt_pics += 1

    def check_and_get_gifs(self, msg):
        """Check if msg is containing gifs and stored it in self.gifs.

        Parameters
        ----------
        msg : dict
            JSON Formatted Facebook message.

        """
        for attachment in msg["attachments"]:
            if (attachment["attach_type"] == "animated_image" and
                    attachment["preview_url"] is not None):

                if (self.mode == FBParserMode.REPORT
                        or self.mode == FBParserMode.DL):
                    self.gifs += attachment["preview_url"] + "\n"

                if self.mode == FBParserMode.DL:
                    dl_path = self.output_convers \
                        + FBDataTypes.GIFS.value + os.sep \
                        + attachment["name"]
                    self.futures[self.executor.
                                 submit(self.dl_file,
                                        attachment["preview_url"],
                                        dl_path)] = attachment["preview_url"]

                self.cnt_gifs += 1

    def check_and_get_videos(self, msg):
        """Check if msg is containing videos and stored it in self.videos.

        Parameters
        ----------
        msg : dict
            JSON Formatted Facebook message.

        """
        for attachment in msg["attachments"]:
            if (attachment["attach_type"] == "video" and
                    attachment["url"] is not None):

                if (self.mode == FBParserMode.REPORT
                        or self.mode == FBParserMode.DL):
                    self.videos += attachment["url"] + "\n"

                if self.mode == FBParserMode.DL:
                    dl_path = self.output_convers \
                        + FBDataTypes.VIDEOS.value + os.sep \
                        + attachment["name"]
                    self.futures[self.executor.
                                 submit(self.dl_file,
                                        attachment["url"],
                                        dl_path)] = attachment["url"]

                self.cnt_videos += 1

    def check_and_get_files(self, msg):
        """Check if msg is containing files and stored it in self.files.

        Parameters
        ----------
        msg : dict
            JSON Formatted Facebook message.

        """
        for attachment in msg["attachments"]:
            if (attachment["attach_type"] == "file"
                    and attachment["url"] is not None):

                if (self.mode == FBParserMode.REPORT
                        or self.mode == FBParserMode.DL):
                    self.files += attachment["url"] + "\n"

                if self.mode == FBParserMode.DL:
                    dl_path = self.output_convers \
                        + FBDataTypes.FILES.value + os.sep \
                        + attachment["name"]
                    self.futures[self.executor.
                                 submit(self.dl_file,
                                        attachment["url"],
                                        dl_path)] = attachment["url"]

                self.cnt_files += 1

    def check_and_get_links(self, msg):
        """Check if msg is containing links and stored it in self.links.

        Parameters
        ----------
        msg : dict
            JSON Formatted Facebook message.

        """
        regex_get_url_from_uri = "https:\/\/l.facebook.com\/l.php.u=(.*?)&h="

        for attachment in msg["attachments"]:
            if (attachment["attach_type"] == "share" and
                    attachment["share"]["uri"] is not None):

                match = re.search(regex_get_url_from_uri,
                                  attachment["share"]["uri"])
                if match is not None:
                    self.links += parse.unquote(match.group(1)) + "\n"
                else:
                    self.links += attachment["share"]["uri"] + "\n"

                self.cnt_links += 1
        if "ranges" in msg:
            for link_range in msg["ranges"]:
                self.links += link_range["entity"]["url"] + "\n"
                self.cnt_links += 1

        return 0

    def parse(self, to_stdout=False, verbose=False):
        """Main loop for iterating over all the JSON conversations.

        Parameters
        ----------
        to_sdout : bool
           Print traces to stdout when it is True. The default is False.
        verbose: bool
            Print additionnal traces (one for each saved file) to stdout
            when it is True (`to_stdout` must be also True).

        """
        if FBDataTypes.ALL in self.data:
            functions = [self.check_and_get_msg, self.check_and_get_pics,
                         self.check_and_get_gifs, self.check_and_get_videos,
                         self.check_and_get_files, self.check_and_get_links]

        else:
            functions = []
            if FBDataTypes.MESSAGES in self.data:
                functions.append(self.check_and_get_msg)
            if FBDataTypes.PICTURES in self.data:
                functions.append(self.check_and_get_pics)
            if FBDataTypes.GIFS in self.data:
                functions.append(self.check_and_get_gifs)
            if FBDataTypes.VIDEOS in self.data:
                functions.append(self.check_and_get_videos)
            if FBDataTypes.FILES in self.data:
                functions.append(self.check_and_get_files)
            if FBDataTypes.LINKS in self.data:
                functions.append(self.check_and_get_links)

        if self.infile_json:
            for file in self.infile_json:
                if to_stdout:
                    print("[+] - Loading JSON from file '{}'".format(file))
                self.init_parser_for_next(file)
                self.process_msgs(functions)
                if to_stdout:
                    print("[+]     - JSON parsed succesfully, saving results "
                          "inside folder '" + str(self.output) + "'")
                    self.print_summary_report()
                if self.check_and_get_msg in functions:
                    dict_c = {self.convers_id: self.convers[self.convers_id]}
                    self.msgs = format_convers_metadata(dict_c,
                                                        self.participants) \
                        + "\n" + "-" * 79 + "\n\n" + self.msgs
                self.write_reports_to_file()
                self.wait_threads(to_stdout, verbose)

        elif self.json_msgs:
            self.process_msgs(functions)
            if to_stdout:
                print("[+]     - JSON parsed succesfully, saving results "
                      "inside folder '" + str(self.output) + "'")
                self.print_summary_report()
            self.write_reports_to_file()
            self.wait_threads(to_stdout, verbose)

    def process_msgs(self, functions):
        """Aply `functions` to each message in `self.json_msgs`.

        Parameters
        ----------
        functions: array_like
            Array of functions to apply to `self.json_msgs`.

        """
        for msg in self.json_msgs:
            if self.common_checks(msg):
                    for function in functions:
                        function(msg)

    def wait_threads(self, to_stdout=False, verbose=False):
        """Wait download threads to be finished.

        Parameters
        ----------
        to_stdout : bool
           Print traces to stdout when it is True. The default is False.
        verbose: bool
            Print additionnal traces (one for each saved file) to stdout
            when it is True (`to_stdout` must be also True).

        Notes
        -----
        if to_stdout is False, exceptions won't be printed but threw.

        """
        if self.mode == FBParserMode.DL:
            if to_stdout:
                print("[+]     - Waiting for downloading threads to finished")

            loading_thread = PrintLoading(len(self.futures))
            loading_thread.daemon = True
            loading_thread.start()
            for future in futures.as_completed(self.futures):
                try:
                    future.result()
                    if to_stdout and verbose:
                        print("[+]     - File '" + self.futures[future]
                              + "' saved")
                except Exception as e:
                    if to_stdout:
                        print("[+]     - File '" + self.futures[future]
                              + "' generated an exception: " + str(e))
                    else:
                        raise e
                finally:
                    loading_thread.cnt -= 1

            loading_thread.run_flag = False
            loading_thread.join()

    def dl_file(self, url, filelocation):
        """Download file function.

        Parameters
        ----------
        url : str
           URL where to download the file.
        filelocation : str
            Path where to save file.

        """
        r = requests.get(url, stream=True)
        with open(filelocation, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if self.quit:
                    break
                if chunk:
                    f.write(chunk)

    def write_reports_to_file(self):
        """Write all reports inside the `self.output_convers` location.

        See Also
        --------
        FBDataTypes : used for report file names.

        Notes
        -----
        Reports are `msgs`, `pics`, `gifs`, `videos`,
        `files`, `links` content inside a `FBParser` instance.

        Report file names are `FBDataTypes` values with ".txt" appended.

        """
        with open(self.output_convers + FBDataTypes.MESSAGES.value + '.txt',
                  'w') as f:
            f.write(self.msgs)
        with open(self.output_convers + FBDataTypes.PICTURES.value + '.txt',
                  'w') as f:
            f.write(self.pics)
        with open(self.output_convers + FBDataTypes.GIFS.value + '.txt',
                  'w') as f:
            f.write(self.gifs)
        with open(self.output_convers + FBDataTypes.VIDEOS.value + '.txt',
                  'w') as f:
            f.write(self.videos)
        with open(self.output_convers + FBDataTypes.FILES.value + '.txt',
                  'w') as f:
            f.write(self.files)
        with open(self.output_convers + FBDataTypes.LINKS.value + '.txt',
                  'w') as f:
            f.write(self.links)

    def print_summary_report(self):
        """Print to stdout a summary report.

        The summary reports contains a cnt variable for each data types
        (msgs, pics, gifs, videos, files and links)

        """
        print(self.summary_report_fmt.format(self.cnt_msgs, self.cnt_pics,
                                             self.cnt_gifs,
                                             self.cnt_videos,
                                             self.cnt_files,
                                             self.cnt_links
                                             ))
