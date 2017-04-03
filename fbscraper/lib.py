#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""general_functions module.

This module contains general functions (some sort of a library).

"""
import sys
import time
from datetime import datetime
from itertools import cycle
from threading import Thread

from enum import Enum

OUTPUT_DEFAULT_FOLDER = "output"


class FBDataTypes(Enum):
    """Enumeration containing all data types which can be retrieved.

    Notes
    -----
    These `Enum` values are also used for writing reports
    in the `FBParser` class.

    """

    ALL = "all"
    MESSAGES = "messages"
    PICTURES = "pictures"
    GIFS = "gifs"
    VIDEOS = "videos"
    FILES = "files"
    LINKS = "links"


class FBParserMode(Enum):
    """Enumeration containing FBParser mode that can be used.

    Attributes
    ----------
    REPORT : FBParserMode
        REPORT mode only save URLs.
    DL : FBParserMode
        DL mode save URLs and download it.

    """

    REPORT = "report"
    DL = "dl"


class FBConversType(Enum):
    """Enumeration for type conversation (group conversation)."""

    GROUP = "group"
    USER = "user"


class FBResponseError(Exception):
    """Exception when the user not authenticated from Facebook."""

    pass


class FBUnknownConvers(Exception):
    """Exception when conversation ID does not match any conversation.

    If it can not be match, it is usually that the conversation ID is
    malformed, or the user does not have the permissions to this conversation.

    """

    pass


class PrintLoading(Thread):
    """Simple thread for printing a loading line with a counter."""

    loading_list = cycle(["[-]", "[\\]", "[/]"])

    def __init__(self, cnt):
        """__init___ method.

        Parameters
        ----------
        cnt : int
            First value of the counter to print

        Attributes
        ----------
        run_flag : bool
            The thread will be running only if the run_flag is True.
        """
        Thread.__init__(self)
        self.run_flag = True
        self.cnt = cnt

    def run(self):
        """Run method."""
        notification_fmt = "{}     - Remaining downloads : {} "
        max_len_printed = len("[-]" + notification_fmt
                              + str(self.cnt)) - 4
        while self.run_flag:
            print(" " * (max_len_printed + 1) + "\r", end='')
            print(notification_fmt.format(next(self.loading_list),
                                          self.cnt), end='')
            sys.stdout.flush()
            time.sleep(0.2)
        print(" " * (max_len_printed + 1) + "\r", end='')
        print("[+]     - Remaining downloads : 0 \n", end='')
        sys.stdout.flush()


def format_convers_metadata(convers, participants):
    """Format conversations metadata.

    Parameters
    ----------
    convers : array_like
        Array of `dict` conversations to format.

    Returns
    -------
    str
        Return the formatted metadata string.

    """
    metadata_fmt = "[+] - ID: '{}' - Name: '{}' - Last msg: '{}' - Type:" \
                   " '{}' - Status: '{}' - Users: '{}'\n"
    formatted_metadata = ""
    for c in convers:
        current_convers = convers[c]
        users = ''.join([participants[u[5:]] + " | "
                         for u in current_convers["participants"]])
        users = users[:-len(" | ")]
        last_msg_date = current_convers["last_message_timestamp"] / 1000
        formatted_metadata += (metadata_fmt
                               .format(c, current_convers["name"],
                                       datetime.fromtimestamp(last_msg_date)
                                       .strftime('%Y-%m-%d %H:%M:%S'),
                                       current_convers["type"].value,
                                       current_convers["status"], users))
    return formatted_metadata.rstrip()


def build_fmt_str_from_enum(enums):
    """Build formatted string from enum list.

    Parameters
    ----------
    enums: array_like
        Array of enums.

    Returns
    -------
    str
        Return the formatted string.

    """
    formatted = "["
    for e in enums:
        formatted += "'" + e.value.lower() + "', "
    formatted = formatted[:-len(", ")] + "]"
    return formatted
