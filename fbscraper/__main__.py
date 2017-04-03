#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fbscraper package.

This module is used for parsing or dumping a FB JSON (see help
command for further details).

Examples
--------
    Using the CLI:
        $ ./fbscraper.py dumper -s 10000 -c request_data.txt
        $ ./fbscraper.py parser -m dl -d all -i output/*/complete.json
        -c request_data.txt

    Using as the module:
        >>> from fbscraper.parser import FBParser
        >>> fb_parserr = FBParser('complete.json', 'dl', 'pictures')
        >>> fb_parser.parse(to_stdout=True)

"""
import argparse
import sys

from fbscraper.dumper import FBDumper
from fbscraper.lib import FBDataTypes, FBParserMode, FBResponseError, \
                           OUTPUT_DEFAULT_FOLDER, \
                           format_convers_metadata, \
                           build_fmt_str_from_enum
from fbscraper.parser import FBParser


def check_positive_int(value):
    """Check positive int."""
    ivalue = int(value)
    if ivalue < 0:
        raise argparse.ArgumentTypeError("{} is an invalid positive"
                                         "int value".format(value))
    return ivalue


def check_positive_and_not_zero_int(value):
    """Check positive and not zero int."""
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("{} is an invalid positive"
                                         "int value".format(value))
    return ivalue


def check_positive_float(value):
    """Check positive float."""
    fvalue = float(value)
    if fvalue < 0:
        raise argparse.ArgumentTypeError("{} is an invalid positive"
                                         "float value".format(value))
    return fvalue


def main():
    """Main function.

    This method will parse arguments and depending on which tool is selected
    (**dumper** or **parser**) and executed the corresponding main function
    (`dumper_tool_main` or `parser_tool_main`).

    Returns
    -------
    int
        0 on success.

    See Also
    --------
    dumper_tool_main : method executed for the **dumper** tool.
    parser_tool_main : method executed for the **parser** tool.

    Notes
    -----
    See usages at the top of the module.

    Use the help command for more information.

    """
    parser = argparse.ArgumentParser(description="Script for parsing a FB"
                                                 " JSON conversation and ")
    subparsers = parser.add_subparsers(help='Tool to use')
    dumper_parser = subparsers.add_parser('dumper', help='Dumper tool. '
                                          'See help: fbscraper dumper -h')
    parser_parser = subparsers.add_parser('parser', help='Parser tool. '
                                          'See help: fbscraper parser -h')

    dumper_parser.add_argument('-id', "--convers-id", nargs='*',
                               help="Conversation IDs to dump")

    dumper_parser.add_argument('-s', "--size", type=check_positive_int,
                               default=2000,
                               help="Number of messages to retrieve for "
                                    "each request")

    dumper_parser.add_argument('-off', "--offset", type=check_positive_int,
                               default=0,
                               help="Do not retrieve the last 'n' messages'")

    dumper_parser.add_argument('-t', "--timer", type=check_positive_float,
                               default=1,
                               help="Do not retrieve the last 'n' messages'")

    dumper_parser.add_argument('-meta', '--metadata', action="store_true",
                               help="If this option is used, conversations "
                                    " not dumped. Conversations metadata "
                                    "are printed")

    parser_parser.add_argument('-m', '--mode', required=True,
                               type=FBParserMode,
                               help="Report mode only save URLs inside files. "
                                    "The dl mode additionnaly download it. "
                                    "MODE may be one of "
                                    + build_fmt_str_from_enum(FBParserMode))

    parser_parser.add_argument("-d", "--data", nargs="+",
                               type=FBDataTypes,
                               default=[FBDataTypes.ALL],
                               help="Data to retrieve from the --infile file. "
                                    "DATA may be one or many of "
                                    + build_fmt_str_from_enum(FBDataTypes))

    parser_parser.add_argument("-i", "--infile", nargs='+',
                               help="File to parse and try to retrieve data "
                                    "from the --data types")

    parser_parser.add_argument('-t', "--threads",
                               type=check_positive_and_not_zero_int, default=4,
                               help="Number of threads for dl mode")

    dumper_parser.set_defaults(func=dumper_tool_main)
    parser_parser.set_defaults(func=parser_tool_main)
    for subparser in [dumper_parser, parser_parser]:
        subparser.add_argument("-c", "--cookie", type=argparse.FileType("r"),
                                     required=True,
                                     help="File to parse for retrieving"
                                          "headers and post data for "
                                          "intializing the scraper")

        subparser.add_argument("-v", "--verbose", action="store_true",
                                     help="Increase output verbosity")

        subparser.add_argument('-o', "--output",
                                     default=OUTPUT_DEFAULT_FOLDER,
                                     help="Output folder where to save data."
                                          "This folder may be common to all ID"
                                          "conversations dumped or parsed."
                                          "The creation of a folder with the"
                                          "conversation ID is automatically "
                                          "created")

    args = parser.parse_args()
    if hasattr(args, "func"):
        if args.verbose:
            print("[+] - Args: " + str(args))
        try:
            return args.func(args)
        except KeyError as e:
            print("[+] - KeyError exception generated. It is probably due "
                  "to a change in the JSON conversation format. Please open "
                  "an issue on the Github repository, with your JSON file "
                  "attached.\nException : {0!r}".format(e))
            return 1
    else:
        parser.print_usage()


def dumper_tool_main(args):
    """Main function for the **dumper** tool.

    Parameters
    ----------
    args : Namespace
        Arguments passed by the `ArgumentParser`.

    This method will dump a Facebook conversation and save it to two JSON
    formatted files (one for JSON, one for 'pretty' JSON) depending on
    the arguments passed.

    See Also
    --------
    main : method used for parsing arguments
    dump : method executed for the **dumper** tool.

    """
    with args.cookie as f:
        user_post_data = f.read()

    fb_dumper = FBDumper(args.convers_id, user_raw_data=user_post_data,
                         chunk_size=args.size, timer=args.timer,
                         output=args.output)
    if args.metadata:
        print("[+] - Printing conversations metadata (total: {})"
              .format(len(fb_dumper.convers)))
        print(format_convers_metadata(fb_dumper.convers,
                                      fb_dumper.participants))
        return 0

    if args.convers_id:
        print("[+] - Dumping JSON from {} conversations"
              .format(len(args.convers_id)))
    else:
        print("[+] - Dumping JSON from all conversations (total: {})"
              .format(len(fb_dumper.convers)))

    try:
        fb_dumper.dump(to_stdout=True, verbose=args.verbose)
    except FBResponseError as e:
        print("[+]     - Error Occured, Facebook error summary : '{}'"
              .format(e))

    return 0


def parser_tool_main(args):
    """Main function for the **parser** tool.

    This method will parse a JSON formatted Facebook conversation,
    reports informations and retrieve data from it, depending on the
    arguments passed.

    Parameters
    ----------
    args : Namespace (dict-like)
        Arguments passed by the `ArgumentParser`.

    See Also
    --------
    FBParser: Class used for the **parser** tool.
    main : method used for parsing arguments

    """
    with args.cookie as f:
        user_raw_data = f.read()

    print("[+] - Parsing JSON for {} files".format(len(args.infile)))

    data_formatted = build_fmt_str_from_enum(args.data)
    print("[+] - Parsing JSON to retrieve {}".format(data_formatted))

    fb_parser = FBParser(user_raw_data,
                         infile_json=args.infile, mode=args.mode,
                         data=args.data, output=args.output,
                         threads=args.threads)
    fb_parser.parse(to_stdout=True, verbose=args.verbose)
    print("[+]     - JSON parsed succesfully, saving results "
          "inside folder '" + str(args.output) + "'")

    return 0


if __name__ == '__main__':
    sys.exit(main())
