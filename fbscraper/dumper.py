"""dumper module.

This module is used for dumping a FB JSON conversation.

Examples
--------
>>> from fbscraper.dumper import FBDumper
>>> fb_dumper = FBDumper(infile_user_raw_data="request_data.txt",
chunk_size=10000)
>>> fb_dumper.dump(to_stdout=True)

"""

import copy
import json
import os
import re
import time

import requests
from unidecode import unidecode

from fbscraper.lib import FBConversType, FBResponseError, FBUnknownConvers, \
                           OUTPUT_DEFAULT_FOLDER


class FBDumper(object):
    """Class for dumping Facebook JSON conversations."""

    _DICT_FB_TYPES = {FBConversType.GROUP.value: "thread_fbids",
                      FBConversType.USER.value: "user_ids"}
    _url_convers = "https://www.facebook.com/ajax/mercury/thread_info.php"
    _url_convers_list = "https://www.facebook.com/ajax/mercury/" \
                        "threadlist_info.php"
    _end_flag = "end_of_history"
    _basic_headers = {
        "origin": "https://www.facebook.com",
        "accept-encoding": "gzip,deflate",
        "accept-language": "en-US,en;q=0.8",
        "pragma": "no-cache",
        "user-agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/"
        "537.36 (KHTML, like Gecko) Chrome/44.0.2403.107 Safari/537.36",

        "content-type": "application/x-www-form-urlencoded",
        "accept": "*/*",
        "cache-control": "no-cache",
        "referer": "https://www.facebook.com/messages/toto"
    }
    _chunk_size_convers = 1000

    def __init__(self, convers_ids=None, user_raw_data=None,
                 infile_user_raw_data=None, chunk_size=2000,
                 timer=1, output=OUTPUT_DEFAULT_FOLDER):
        """__init__ method.

        Parameters
        ----------
        convers_ids : str, optional
            Conversation IDs to dump. If None every conversations
            will be dumped when calling `dump` instance method.
        user_raw_data : str, optional
            String containing user headers and POST data
        infile_user_raw_data : str, optional
            Filepath from where to load user headers and POST data
        chunk_size : int, optional
           Number of messages to retrieve for each request.
           The default is 2000.
        timer : int, optional
           Timer between each request made by the dumper. The default is 1.
        output : str, optional
            Folder output where to save data. May be common between
            conversation dumped or parsed.

        Raises
        ------
        ValueError
            When both a `user_raw_data` or a `infile_user_raw_data`
            are provided.

            When the number of the `chunk_size` is inferior or equal to 0.

            When the number of the `timer` is inferior to 0.

        """
        self.convers_ids = convers_ids

        if bool(user_raw_data) ^ bool(infile_user_raw_data):
            if user_raw_data:
                self.user_raw_data = user_raw_data
            else:
                with open(infile_user_raw_data, 'r') as f:
                    self.user_raw_data = f.read()
        else:
            raise ValueError('You should either provide a string with your'
                             'POST data user_raw_data or a filepath as '
                             'infile_user_raw_data.')
        if chunk_size <= 0:
            raise ValueError('You should provide a postive integer value for '
                             'the chunk_size. Value : {}'.format(chunk_size))
        self.chunk_size = chunk_size

        if timer < 0:
            raise ValueError('You should provide a postive or 0 integer value'
                             'the timer. Value : {}'.format(timer))
        self.timer = timer

        self.output = os.path.join(output, '')
        os.makedirs(self.output, exist_ok=True)

        self.headers, self.post_data = self.get_post_data()
        self.convers, self.participants = self.get_all_convers_metadata()

    def get_post_data(self):
        """Method for getting headers and POST data.

        These data are mandatory for forging a valid POST request to retrieve
        conversations messages.

        Returns
        -------
        tuple
            Containing headers and POST data dictionnaries
            (headers, post_data).

        """
        headers = copy.deepcopy(self._basic_headers)
        post_data = {}

        headers['cookie'] = re.search('cookie:(.*?)\n',
                                      self.user_raw_data).group(1)

        post_data['__user'] = re.search('__user:(.*)\n',
                                        self.user_raw_data).group(1)
        post_data['__a'] = re.search('__a:(.*)\n',
                                     self.user_raw_data).group(1)
        post_data['__dyn'] = re.search('__dyn:(.*)\n',
                                       self.user_raw_data).group(1)
        post_data['__req'] = re.search('__req:(.*)\n',
                                       self.user_raw_data).group(1)
        post_data['fb_dtsg'] = re.search('fb_dtsg:(.*)\n',
                                         self.user_raw_data).group(1)
        post_data['__rev'] = re.search('__rev:(.*)\n',
                                       self.user_raw_data).group(1)

        return (headers, post_data)

    def make_request(self, url, data, to_stdout=False, verbose=False):
        """Method for making the request to Facebook and return the JSON.

        Parameters
        ----------
        url: str
            URL where making the request.
        data: dict
            POST Data containing the payload for dumping (messages or
            conversations list).
        to_sdout : bool
           Print traces to stdout when it is True. The default is False.
        verbose: bool
            Print additionnal traces to stdout.

        Raises
        ------
        FBResponseError
            When Facebook responds with an errort report. Usually it means
            that your POST data and headers are expired.

        """
        r = requests.post(url, headers=self.headers,
                          data=data)
        raw_response = r.text[9:]
        json_data = json.loads(raw_response)

        if "error" in json_data:
            raise FBResponseError(json_data["errorSummary"])

        return json_data

    def build_data(self, convers_id, convers_type, offset, timestamp):
        """Method for building the final data dictionnary request.

        Parameters
        ----------
        convers_id : str
            Conversation ID to dump.
        convers_type: FBConversType
            Type of conversation.
        offset: int
            The JSON is returned as multiple chunks. Therefore, offsetting
            requests are needed to get the correct chunk.
        timestamp : str
            Timestamp passed between each request and response.
        output : str, optional
            Folder output where to save data. May be common between
            conversation dumped or parsed.

        Returns
        -------
        dict
            The new `dict` containing all dynamic data at which we append the
            data skeleton.

        """
        data_for_msgs = {
            "messages[" + self._DICT_FB_TYPES[convers_type.value] + "]["
            + convers_id + "][offset]": str(offset),

            "messages[" + self._DICT_FB_TYPES[convers_type.value] + "]["
            + convers_id + "][limit]": str(self.chunk_size),

            "messages[" + self._DICT_FB_TYPES[convers_type.value] + "]["
            + convers_id + "][timestamp]": timestamp,

            "client": "web_messenger"

        }
        data_for_msgs.update(self.post_data)
        return data_for_msgs

    def get_all_convers_metadata(self):
        """Method for getting all conversations metadata (inbox & archived)."""
        convers = {}
        participants = {}
        for convers_status in ["inbox", "archived"]:
            offset = 0
            is_dumped = False
            while not is_dumped:
                if convers_status == "inbox":
                    data_for_msgs = {
                        convers_status + "[offset]": str(offset),
                        convers_status + "[limit]":
                            str(self._chunk_size_convers),
                        convers_status + "[filter]": "",
                        "client": "web_messenger"

                    }
                elif convers_status == "archived":
                    data_for_msgs = {
                        "action:" + convers_status + "[offset]": str(offset),
                        "action:" + convers_status + "[limit]":
                            str(self._chunk_size_convers),
                        "action:" + convers_status + "[filter]": "",
                        "client": "web_messenger"

                    }
                data_for_msgs.update(self.post_data)
                json_data = self.make_request(self._url_convers_list,
                                              data_for_msgs)
                json_threads = json_data["payload"]["threads"]
                json_participants = json_data["payload"]["participants"]
                current_convers = {}

                for participant in json_participants:
                    participants[participant["fbid"]] = participant["name"]

                for c in json_threads:
                    if c["thread_type"] == 2:
                        current_convers["type"] = FBConversType.GROUP
                        current_convers["name"] = c["name"]
                    elif c["thread_type"] == 1:
                        current_convers["type"] = FBConversType.USER
                        current_convers["name"] = participants[c["other_user_"
                                                                 "fbid"]
                                                               ]
                    current_convers["status"] = convers_status
                    current_convers["participants"] = c["participants"]
                    current_convers["last_message_timestamp"] = c["last_messag"
                                                                  "e_timestamp"
                                                                  ]

                    convers[c["thread_fbid"]] = copy.deepcopy(current_convers)

                if len(json_threads) < self._chunk_size_convers:
                    is_dumped = True
                else:
                    offset += self._chunk_size_convers

        return (convers, participants)

    def dump(self, to_stdout=False, verbose=False):
        """Method for dumping Facebook JSON Conversations.

        Parameters
        ----------
        to_sdout : bool
           Print traces to stdout when it is True. The default is False.
        verbose: bool
            Print additionnal traces to stdout.

        Notes
        -----
        If `self.convers_ids` is None every conversations
        will be dumped.

        """
        if self.convers_ids:
            convers_ids = self.convers_ids
        else:
            convers_ids = []
            for c in self.convers:
                convers_ids.append(c)

        for c in convers_ids:

            if c not in self.convers:
                raise FBUnknownConvers("Conversation ID '{}' does not match "
                                       "any conversation from the user."
                                       .format(c))

            if to_stdout:
                print("[+] - Dumping JSON from conversation with ID: '{}' "
                      "and name: '{}'".format(c, unidecode(self.convers[c]
                                                           ["name"])))

            messages = []
            current_convers = self.convers[c]
            offset = 0
            timestamp = "0"
            json_data = {"payload": {}}

            while self._end_flag not in json_data["payload"]:

                data_for_msgs = self.build_data(c,
                                                current_convers["type"],
                                                offset, timestamp)

                if to_stdout:
                    print("[+]     - Retrieving messages " + str(offset)
                          + "-" + str(self.chunk_size + offset))

                json_data = self.make_request(self._url_convers,
                                              data_for_msgs, True)

                messages = json_data['payload']['actions'] + messages
                timestamp = json_data['payload']['actions'][0]['timestamp']

                offset = offset + self.chunk_size
                time.sleep(self.timer)
            filelocation = self.output + c + " - " \
                + unidecode(self.convers[c]["name"]) + os.sep
            os.makedirs(filelocation, exist_ok=True)
            self.write_dump_to_file(messages, filelocation, 2)

    def write_dump_to_file(self, dump, filelocation, mode=0,
                           base_filename='complete'):
        """Write JSON dump to files.

        Parameters
        ----------
        mode : int, optional
            Integer to know if you want to save raw JSON (`mode` == 0),
            'pretty' JSON (`mode` == 1) or both (`mode` == 2).

        base_filename : str, optional
            base_filename to construct the final filename where to save
            JSON dump(s).

        Notes
        -----
        Raw JSON filename is : `base_filename` + '.json'

        Pretty JSON filename is : `base_filename` + 'pretty.json'

        """
        if mode < 0 or mode > 2:
            raise ValueError("Mode parameter must be 0, 1 or 2. Mode : {}"
                             .format(mode))
        if mode == 0 or mode == 2:
            with open(filelocation + base_filename + ".json", 'w') as f:
                json.dump(dump, f)

        if mode == 1 or mode == 2:
            with open(filelocation + base_filename + ".pretty.json", 'w') as f:
                json.dump(dump, f, indent=4)
