import argparse
import ConfigParser
import gzip
import logging
import re
import sys

from operator import itemgetter
from os import listdir, walk
from os.path import join
from time import gmtime, strftime


def median(lst):
    n = len(lst)
    if n < 1:
            return None
    if n % 2 == 1:
            return sorted(lst)[n//2]
    else:
            return sum(sorted(lst)[n//2-1:n//2+1])/2.0


def get_last_report_file(report_dir):
    """

    :param report_dir:
    :return:
    """
    report_files = []
    for root, dirs, files in walk(report_dir):
        for file in files:
            if file.startswith("report-") and file.endswith(".html"):
                report_files.append(file)
    return sorted(report_files)[-1]


def get_last_log_file(log_dir):
    """Walks on dir, find all nginx logs and return last log_file name

    :param log_dir: directory with logs
    :return: str: log file name
    """

    log_files = []
    for root, dirs, files in walk(log_dir):
        for file in files:
            if file.startswith("nginx-access-ui.log"):
                log_files.append(file)
    return sorted(log_files)[-1]


def parse_log_file(log_file):
    """Parse log file and return parsed dict with urls and request times
    :param: log_dir
    :param log_file:
    :return: dict
    """
    regexps = [(r'\d+.\d+.\d+.\d+\s+'
                r'\S+\s+\S+\s+\S+\s+\S+\s+\S+\s+'
                r'(\S+)\s+\S+\S+\s+\S+\s+\S+\s+".*?"\s+'
                r'".*?"\s+".?"\s+".*?"\s+".*?"\s+(\S+)'),
               (r'\d+.\d+.\d+.\d+\s+'
                r'\S+\s+\S+\s+\S+\s+\S+\s+'
                r'\S+\s+(\S+)\s+\S+\S+\s+\S+\s+\S+\s+".*?"\s+'
                r'".*?"\s+".*?"\s+".*?"\s+".*?"\s+(\S+)')]
    if log_file.endswith(".gz"):
        file = gzip.open(log_file)
    else:
        file = open(log_file)
    statistics = {'urls': {},
                  'file_name': log_file}
    unparsed_events = 0
    events = 0
    for l in file.readlines():
        events += 1
        parsed_ratio = 100 * (events - unparsed_events) / events
        for regexp in regexps:
            if isinstance(l, (bytes, bytearray)):
                data = re.search(regexp, l.decode())
            else:
                data = re.search(regexp, l)
        if parsed_ratio > 50:
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
    file.close()
    return statistics


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


def generate_report(statistics, report_path, report_size):
    """Get statistics file and generate report

    :param statistics:
    :return:
    """
    with open("./report.html", 'r') as report_template:
        report = report_template.read()
    top_urls = get_top_urls(statistics, report_size)
    url_list = []
    for url in top_urls.values():
        url_dict = {"count": get_count(statistics, url),
                    "time_avg": get_time_avg(statistics, url),
                    "time_max": get_time_max(statistics, url),
                    "time_sum": get_time_sum(statistics, url),
                    "url": url, "time_med": get_med(statistics, url),
                    "time_perc": get_time_perc(statistics, url),
                    "count_perc": get_count_perc(statistics, url)}
        url_list.append(url_dict)
    date = get_log_file_date(statistics['file_name'])
    new_date = ".".join([date[0:4], date[4:6], date[6:9]])
    with open(join(report_path, "report-%s.html" % new_date),
              "w") as new_report:
        data = report.replace("table_json", str(url_list))
        new_report.write(data)


def get_count(statistics, url):
    """URL Count
    """
    return statistics['urls'][url]['count']


def get_count_perc(statistics, url):
    """URL percent count from overall URLS

    :param log_file:
    :return:
    """
    url_count = statistics['urls'][url]['count']
    total_events = statistics["total_events"]
    return 100 - (100 * (total_events - url_count) / total_events)


def get_time_sum(statistics, url):
    """$request_time sum for URL
    :param log_file:
    :return:
    """
    return sum(statistics['urls'][url]['times'])


def get_time_perc(statistics, url):
    """$request_time sum per URL in % from overall request time

    :param log_file:
    :return:
    """
    all_request_times = []
    for url in statistics['urls']:
        for request_time in statistics['urls'][url]['times']:
            all_request_times.append(request_time)
    overall_request_time = sum(all_request_times)
    url_request_time_sum = sum(statistics['urls'][url]['times'])
    return 100 - (
        100 * (
            overall_request_time - url_request_time_sum
        ) / overall_request_time)


def get_time_avg(statistics, url):
    """time_avg $request_time per URL

    :param log_file:
    :return:
    """
    return sum(
        statistics['urls'][url]['times']) / float(
        len(statistics['urls'][url]['times']))


def get_log_file_date(file_name):
    """

    :param file_name:
    :return:
    """
    if file_name.endwith(".gz"):
        return file_name.lstrip('nginx-access-ui.log-').rstrip(".gz")
    else:
        return file_name.split("-")[-1]


def get_time_max(statistics, url):
    """time_max  $request_time per URL

    :param log_file:
    :return:
    """
    return max(statistics['urls'][url]['times'])


def get_med(statistics, url):
    """time_med med $request_time per URL
    :param log_file:
    :return:
    """
    return median(statistics['urls'][url]['times'])


def main():
    FORMAT = '%(asctime)s %(levelname)s %(message)s'
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
    args = parser.parse_args()

    if config_parser:
        Config = ConfigParser.ConfigParser()
        Config.read(args.config)
        nginx_dir = Config.get("LogAnalyzer", 'NGINX_LOG')
        report_dir = Config.get("LogAnalyzer", 'REPORT_DIR')
        log_dir = Config.get("LogAnalyzer", 'LOG_DIR')
        report_size = Config.get("LogAnalyzer", 'REPORT_SIZE')
        if log_dir is not None:
            logging.basicConfig(format=FORMAT, datefmt='%Y.%m.%d %H:%M:%S',
                                filename=join(log_dir, 'log_analyzer.log'),
                                filemode='a+', level=logging.DEBUG)
        else:
            logging.basicConfig(format=FORMAT, datefmt='%Y.%m.%d %H:%M:%S',
                                stream=sys.stdout, level=logging.DEBUG)
    else:
        nginx_dir = args.nginx_dir
        report_dir = args.report_dir
        report_size = args.report_size
        log_dir = args.log_dir
        if args.log_dir is not None:
            logging.basicConfig(format=FORMAT,
                                datefmt='%Y.%m.%d %H:%M:%S',
                                filename=join(args.log_dir,
                                              'log_analyzer.log'),
                                filemode='a+', level=logging.DEBUG)
        else:
            logging.basicConfig(format=FORMAT, datefmt='%Y.%m.%d %H:%M:%S',
                                stream=sys.stdout, level=logging.DEBUG)
    try:
        nginx_file = get_last_log_file(nginx_dir)
        nginx_file_full_path = join(nginx_dir, nginx_file)
        if listdir(report_dir) == []:
            logging.info("Report directory is empty."
                         " First time running script")
        else:
            last_report_file = get_last_report_file(report_dir)
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
        generate_report(statistics, report_dir, report_size)

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
