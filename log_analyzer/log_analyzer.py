import argparse
import ConfigParser
import glob
import gzip
import logging
import re
import sys

from collections import defaultdict
from operator import itemgetter
from os import listdir
from os.path import exists, join, isdir
from sys import platform as _platform
from time import gmtime, strftime


def median(lst):
    n = len(lst)
    if n < 1:
            return None
    if n % 2 == 1:
            return sorted(lst)[n//2]
    else:
            return sum(sorted(lst)[n//2-1:n//2+1])/2.0


def get_last_file_by_date(dir, nginx=False):
    """

    :param file:
    :param pattern:
    :return:
    """

    if _platform in ["linux", "linux2", 'darwin']:
        delimiter = "/"
    elif _platform in ["win32", "win64"]:
        delimiter = "\\"
    files = []
    if nginx:
        pattern = "nginx-access-ui.log-*"
    else:
        pattern = "report-*.html"
    pathname = join(dir, pattern)
    if isdir(dir):
        for file in glob.glob(pathname):
            files.append(file.split(delimiter)[-1])
    else:
        sys.exit(1)
    return sorted(files)[-1]


def generate_statistics(file, unparsed_ratio):
    """Generate statistics
    :file: str - path to file
    :unparsed_ratio: integer
    :return:
    """
    regexps = [(r'\d+.\d+.\d+.\d+\s+'
                r'\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+'
                r'(\S+)\s+\S+\S+\s+\S+\s+\S+\s+".*?"\s+'
                r'".*?"\s+".?"\s+".*?"\s+".*?"\s+(\S+)'),
               (r'\d+.\d+.\d+.\d+\s+'
                r'\S+\s+\S+\s+\S+\s+\S+\s+'
                r'\S+\s+(\S+)\s+\S+\S+\s+\S+\s+\S+\s+".*?"\s+'
                r'".*?"\s+".*?"\s+".*?"\s+".*?"\s+(\S+)')]
    statistics = {'urls': {}}
    unparsed_events = 0
    events = 0
    for l in file:
        events += 1
        parsed_ratio = 100 * (events - unparsed_events) / events
        for regexp in regexps:
            if isinstance(l, (bytes, bytearray)):
                data = re.search(regexp, l.decode())
            else:
                data = re.search(regexp, l)
        if parsed_ratio > unparsed_ratio:
            if data:
                url = data.group(1)
                request_time = data.group(2)
                if url not in statistics['urls'].keys():
                    statistics["urls"][url] = {}
                    statistics["urls"][url]["count"] = 1
                    statistics["urls"][url]["times"] = []
                    statistics["urls"][url]["times"].append(
                        float(request_time))
                else:
                    statistics["urls"][url]["count"] += 1
                    statistics["urls"][url]["times"].append(
                        float(request_time))
            else:
                unparsed_events += 1
        else:
            logging.ERROR("Too many unparsed events, exiting...")
            sys.exit(1)
    statistics["total_events"] = events
    return statistics


def parse_log_file(log_file, unparsed_ratio):
    """Parse log file and return parsed dict with urls and request times
    :param: log_dir
    :param log_file:
    :return: dict
    """
    if log_file.endswith(".gz"):
        with gzip.open(log_file, 'rb') as file:
            return generate_statistics(file, unparsed_ratio)
    with open(log_file) as file:
        return generate_statistics(file, unparsed_ratio)


def get_top_urls(statistics, report_size):
    """

    :param statistics:
    :return:
    """
    for url in statistics['urls']:
        statistics['urls'][url]['max_time'] = \
            sum(statistics['urls'][url]['times'])
    url_times = {}
    for url in statistics['urls']:
        url_times[url] = statistics['urls'][url]['max_time']
    url_times = {time: url for url, time in url_times.items()}
    if len(url_times) < report_size:
        return dict(sorted(url_times.items(), key=itemgetter(1),
                           reverse=True)[:len(url_times)])
    else:
        return dict(sorted(url_times.items(), key=itemgetter(1),
                           reverse=True)[:report_size])


def generate_report(statistics, report_path, report_size, report_date):
    """Get statistics file and generate report

    :param statistics:
    :return:
    """
    with open("./report.html", 'r') as report_template:
        report = report_template.read()
    top_urls = get_top_urls(statistics, report_size)
    url_list = []
    for url in top_urls.values():
        url_dict = {"count": statistics['urls'][url]['count'],
                    "time_avg": get_time_avg(
                        statistics['urls'][url]['times']),
                    "time_max": get_time_max(
                        statistics['urls'][url]['times']),
                    "time_sum": get_time_sum(statistics['urls'][url]['times']),
                    "url": url,
                    "time_med": get_med(
                        statistics['urls'][url]['times']),
                    "time_perc": get_time_perc(statistics,
                                               statistics[
                                                   'urls'][url]['times']
                                               ),
                    "count_perc": get_count_perc(
                        statistics["total_events"],
                        statistics['urls'][url]['count'])}
        url_list.append(url_dict)
    with open(join(report_path, "report-%s.html" % report_date),
              "w") as new_report:
        data = report.replace("table_json", str(url_list))
        new_report.write(data)


def get_count_perc(total_events, url_count):
    """URL percent count from overall URLs

    :param log_file:
    :return:
    """
    return 100 - (100 * (total_events - url_count) / total_events)


def get_time_sum(times):
    """$request_time sum for URL
    :param log_file:
    :return:
    """
    return sum(times)


def get_time_perc(statistics, url_request_time):
    """$request_time sum per URL in % from overall request time

    :param log_file:
    :return:
    """
    all_request_times = []
    for url in statistics['urls']:
        for request_time in statistics['urls'][url]['times']:
            all_request_times.append(request_time)
    overall_request_time = sum(all_request_times)
    url_request_time_sum = sum(url_request_time)
    return 100 - (
        100 * (
            overall_request_time - url_request_time_sum
        ) / overall_request_time)


def get_time_avg(times):
    """time_avg $request_time for URL

    :param log_file:
    :return:
    """
    return sum(times) / float(len(times))


def get_log_file_date(file_name):
    """

    :param file_name:
    :return:
    """
    if file_name.endswith(".gz"):
        return file_name.lstrip('nginx-access-ui.log-').rstrip(".gz")
    else:
        return file_name.split("-")[-1]


def get_time_max(times):
    """time_max  $request_time per URL

    :param log_file:
    :return:
    """
    return max(times)


def get_med(times):
    """time_med med $request_time per URL
    :param log_file:
    :return:
    """
    return median(times)


def parse_config(config):
    """Parse config from file

    :return:
    """
    if not exists(config):
        sys.exit(1)
    Config = ConfigParser.ConfigParser()
    Config.read(config)
    return (Config.get("LogAnalyzer", 'NGINX_LOG'),
            Config.get("LogAnalyzer", 'REPORT_DIR'),
            Config.get("LogAnalyzer", 'LOG_DIR'),
            Config.get("LogAnalyzer", 'REPORT_SIZE'))


def parse_args():
    parser = argparse.ArgumentParser(
        description='Nginx Log Analyzer Script v1.0')
    subparsers = parser.add_subparsers(help="Provide config file from "
                                            "command line arguments or"
                                            " via config file")
    config_parser = subparsers.add_parser("config")
    config_parser.add_argument('--config', dest="config",
                               help='Path to config file',
                               default="./config.ini")

    cmd_parser = subparsers.add_parser("cmd")
    cmd_parser.add_argument('--nginx_dir', dest="nginx_dir",
                            help="Path to  Nginx logs.", default="./logs")
    cmd_parser.add_argument('--report_dir', dest="report_dir",
                            help="Path to reports", default='./reports')
    cmd_parser.add_argument('--report_size', dest="report_size",
                            help="Report size", default=1000)
    cmd_parser.add_argument('--log_dir', dest="log_dir",
                            help="Directory for script log files",
                            default=None)
    cmd_parser.add_argument('--unparsed_ratio', dest='unparsed_ratio',
                            help="Percentage of unparsed events", default=50)
    args = parser.parse_args()
    if config_parser:
        return parse_config(args.config)
    else:
        return (args.nginx_dir, args.report_dir,
                args.log_dir, args.report_size,
                args.unparsed_ratio)


def main():
    FORMAT = '%(asctime)s %(levelname)s %(message)s'
    options = parse_args()
    nginx_dir = options[0]
    report_dir = options[1]
    log_dir = options[2]
    report_size = options[3]
    if log_dir is not None:
        logging.basicConfig(format=FORMAT, datefmt='%Y.%m.%d %H:%M:%S',
                            filename=join(log_dir, 'log_analyzer.log'),
                            filemode='a+', level=logging.DEBUG)
    else:
        logging.basicConfig(format=FORMAT, datefmt='%Y.%m.%d %H:%M:%S',
                            stream=sys.stdout, level=logging.DEBUG)
    try:
        nginx_file = get_last_file_by_date(nginx_dir, True)
        date = get_log_file_date(nginx_file)
        report_date = ".".join([date[0:4], date[4:6], date[6:9]])
        nginx_file_full_path = join(nginx_dir, nginx_file)
        if not listdir(report_dir):
            logging.info("Report directory is empty."
                         " First time running script")
        else:
            last_report_file = get_last_file_by_date(report_dir)
            last_report_date = last_report_file.lstrip(
                'report-').rstrip('.html').replace(".", "")
            last_log_date = get_log_file_date(nginx_file)
            if last_log_date == last_report_date:
                logging.info("We haven't new reports in %s."
                             " Exiting" % nginx_dir)
                sys.exit(0)
        logging.info("Starting parsing log file %s" % nginx_file)
        statistics = parse_log_file(nginx_file_full_path)
        logging.info("Generating report")
        generate_report(statistics, report_dir, report_size, report_date)

        current_time = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        if log_dir:
            file = open('%s/log_analyzer_%s.ts' % (log_dir, current_time),
                        'w+')
        else:
            file = open('log_analyzer_%s.ts' % current_time, 'w+')
        file.write(current_time)
        file.close()
    except KeyboardInterrupt:
        logging.exception("Keyrbord Interrup from user")
    except IOError:
        logging.exception("Some problems with input output system")


if __name__ == "__main__":
    main()
