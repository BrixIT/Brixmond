from monitor import Monitor
import os, glob, re
from time import sleep
import apache_log_parser


class MonitorApache(Monitor):
    def __init__(self):
        super().__init__()
        self.name = "apache"
        self.accesslogs, self.errorlogs = self.get_log_files()
        self.logformats = self.get_log_formats()

    def get_log_formats(self):
        regex_logformat = re.compile(r'^[\t ]*LogFormat[\t ]+"(.+)"[\t ]+(.+)', re.MULTILINE | re.IGNORECASE)
        config_files = ['/etc/apache2/apache2.conf'] + glob.glob('/etc/apache2/sites-enabled/*.conf') + glob.glob(
            '/etc/apache2/conf-enabled/*.conf')

        logformats = {}

        for file in config_files:
            with open(file) as config_file_handle:
                lines = config_file_handle.read()
                formats = regex_logformat.findall(lines)
                for apache_format in formats:
                    logformats[apache_format[1]] = apache_format[0].replace('\\"', '"')
        return logformats

    def get_log_files(self):
        regex_errorlog = re.compile(r'^[\t ]*ErrorLog[\t ]([\w${}/\.]+)', re.MULTILINE | re.IGNORECASE)
        regex_customlog = re.compile(r'^[\t ]*CustomLog[\t ]([\w${}/\.]+)[\t ]+([^ \n\t]+)', re.MULTILINE | re.IGNORECASE)
        errorlogs = []
        accesslogs = []

        # TODO: Make distro independent
        if os.path.isdir('/etc/apache2/sites-enabled'):
            log_files = ['/etc/apache2/apache2.conf'] + glob.glob('/etc/apache2/sites-enabled/*.conf') + glob.glob(
                '/etc/apache2/conf-enabled/*.conf')
            for vhost_file in log_files:
                with open(vhost_file) as vhost:
                    lines = vhost.read()
                    errorlogs = errorlogs + regex_errorlog.findall(lines)
                    accesslogs = accesslogs + regex_customlog.findall(lines)
        accesslogs_parsed = []
        for line in accesslogs:
            accesslogs_parsed.append((line[0].replace('${APACHE_LOG_DIR}', '/var/log/apache2'), line[1]))

        errorlogs_parsed = []
        for line in errorlogs:
            errorlogs_parsed.append(line.replace('${APACHE_LOG_DIR}', '/var/log/apache2'))
        return list(set(accesslogs_parsed)), list(set(errorlogs_parsed))

    def get_point(self):
        parsers = {}
        for log_format in self.logformats.keys():
            parsers[log_format] = apache_log_parser.make_parser(self.logformats[log_format])

        last_linecount = {}
        while True:
            result = {}
            for file in self.accesslogs:
                filename = file[0]
                fileformat = file[1]
                with open(filename) as logfile:
                    lines = logfile.readlines()
                    start = 0
                    if filename in last_linecount.keys() and len(lines) > last_linecount[filename]:
                        start = last_linecount[filename]
                        last_linecount[filename] = len(lines)
                    new_lines = lines[start:]

                    for line in new_lines:
                        parsed = parsers[fileformat](line[:-1])
                        status = int(parsed['status'])
                        if status in result.keys():
                            result[status] += 1
                        else:
                            result[status] = 1
            yield result
            sleep(60)