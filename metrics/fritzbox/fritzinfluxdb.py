#!/usr/bin/env python3

self_description = """
Fritz InfluxDB is a tiny daemon written to fetch data from a fritz box router and
writes it to an InfluxDB instance.
"""

# import standard modules
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import configparser
import logging
import os
import signal
import time
from datetime import datetime

# import 3rd party modules
import fritzconnection
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS


__version__ = "0.3.1"
__version_date__ = "2021-04-10"
__description__ = "fritzinfluxdb"
__license__ = "MIT"


# default vars
running = True
default_config = os.path.join(os.path.dirname(__file__), 'fritzinfluxdb.ini')
default_log_level = logging.INFO


def parse_args():
    """parse command line arguments

    Also add current version and version date to description
    """

    parser = ArgumentParser(
        description=self_description + f"\nVersion: {__version__} ({__version_date__})",
        formatter_class=RawDescriptionHelpFormatter)

    parser.add_argument("-c", "--config", dest="config_file", default=default_config,
                        help="define config file (default: " + default_config + ")")
    parser.add_argument("-d", "--daemon", action='store_true',
                        help="define if the script is run as a systemd daemon")
    parser.add_argument("-v", "--verbose", action='store_true',
                        help="turn on verbose output to get debug logging")

    return parser.parse_args()


# noinspection PyUnusedLocal
def shutdown(exit_signal, frame):
    """
    Signal handler which ends the loop
    Parameters
    ----------
    exit_signal: int
        signal value
    frame: unused

    """

    global running
    logging.info(f"Program terminated. Signal {exit_signal}")
    running = False


def sanitize_fb_return_data(results):
    """
    Sometimes integers are returned as string
    try to sanitize this a bit

    Parameters
    ----------
    results: dict
        dict of results from fritzconnection call

    Returns
    -------
    dict: sanitized version of results
    """

    return_results = {}
    for instance in results:
        # turn None => 0
        if results[instance] is None:
            return_results.update({instance: 0})
        else:
            # try to parse as int
            try:
                return_results.update({instance: int(results[instance])})
            # keep it a string if this fails
            except ValueError:
                return_results.update({instance: results[instance]})

    return return_results


def query_services(fc, services):
    """
    Query all services from a Fritzbox which are defined in config

    Parameters
    ----------
    fc: fritzconnection.FritzConnection
        initialized fritzconnection handler
    services: dict

    Returns
    -------
    dict: dict of requested and sanitized value_instances
    """

    result = dict()
    error = False

    def _fb_call_action(service_called, action_called):
        """
        Perform actual Fritzbox request

        Parameters
        ----------
        service_called: str
            name of requested service
        action_called: str
            name of requested action

        Returns
        -------
        dict: result from called action or None if an error occurred
        """

        call_result = None
        logging.debug(f"Requesting {service_called} : {action_called}")
        try:
            call_result = fc.call_action(service_called, action_called)
        except fritzconnection.core.exceptions.FritzServiceError:
            logging.error(f"Requested invalid service: {service_called}")
        except fritzconnection.core.exceptions.FritzActionError:
            logging.error(f"Requested invalid action '{action_called}' for service: {service_called}")

        if call_result is not None:
            logging.debug("Request returned successfully")

            for key, value in call_result.items():
                logging.debug(f"Response: {key} = {value}")

        return call_result

    for service, content in services.items():

        for action in content['actions']:

            if 'value_instances' in content:

                this_result = _fb_call_action(service, action)

                if this_result is None:
                    error = True
                    continue

                for instance in content['value_instances']:

                    rewrite_name = None

                    if ':' in instance:
                        instance, rewrite_name = instance.split(':')
                        instance = instance.strip()
                        rewrite_name = rewrite_name.strip()

                    # only keep desired result key
                    if instance in this_result:
                        result.update({rewrite_name if rewrite_name is not None else instance: this_result[instance]})
            else:

                this_result = _fb_call_action(service, action)

                if this_result is None:
                    error = True
                    continue

                result.update(this_result)

    if error is True:
        logging.error("Encountered problems while requesting data. Data might be incomplete.")

    return sanitize_fb_return_data(result)


def read_config(filename):
    """
    Read config ini file and return configparser object

    Parameters
    ----------
    filename: str
        path of ini file to parse

    Returns
    -------
    configparser.ConfigParser(): configparser object
    """

    config = None

    # check if config file exists
    if not os.path.isfile(filename):
        logging.error(f'Config file "{filename}" not found')
        exit(1)

    # check if config file is readable
    if not os.access(filename, os.R_OK):
        logging.error(f'Config file "{filename}" not readable')
        exit(1)

    try:
        config = configparser.ConfigParser(os.environ)
        config.read(filename)
    except configparser.Error as e:
        logging.error("Config Error: %s", str(e))
        exit(1)

    logging.info("Done parsing config file")

    return config


def get_services(config, section_name_prefix):
    """
    Parse all sections matching the prefix to a dict which is used to request services and actions.

    Parameters
    ----------
    config: configparser.ConfigParser
        configparser object with current config
    section_name_prefix: str
        prefix of section names to parse

    Returns
    -------
    dict: a dict of all services and values instances which match the prefix
    """

    this_sections = [s for s in config.sections() if s.startswith(section_name_prefix)]
    this_services = {}
    for s in this_sections:
        this_services.update({config.get(s, 'service'): {'actions': config.get(s, 'actions').split("\n")}})
        if config.has_option(s, 'value_instances'):
            this_services[config.get(s, 'service')].update(
                {'value_instances': config.get(s, 'value_instances').split("\n")})

    return this_services


def main():
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # parse command line arguments
    args = parse_args()

    # set logging
    log_level = logging.DEBUG if args.verbose is True else default_log_level

    if args.daemon:
        # omit time stamp if run in daemon mode
        logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s: %(message)s')

    # read config from ini file
    config = read_config(args.config_file)

    logging.debug ( "CONFIG values")
    logging.debug("url='%s'" % config.get('influx2', 'url',raw=False))
    logging.debug("token='%s'" % config.get('influx2', 'token',raw=False))
    logging.debug("org='%s'" % config.get('influx2', 'org',raw=False))
    logging.debug("bucket='%s'" % config.get('influx2', 'bucket',raw=False))
    logging.debug("host='%s'" % config.get('fritzbox', 'host',raw=False))
    logging.debug("port='%s'" % config.get('fritzbox', 'port',raw=False))
    logging.debug("username='%s'" % config.get('fritzbox', 'username',raw=False))
    logging.debug("password='%s'" % config.get('fritzbox', 'password',raw=False))
    logging.debug("timeout='%s'" % config.get('fritzbox', 'timeout',raw=False))
    logging.debug("ssl='%s'" % config.get('fritzbox', 'ssl',raw=False))


    # set up influxdb handler
    influxdb_client = None
    influxdb_write_api = None
    influxdb_bucket = None
    influxdb_org = None
    try:
        influxdb_client = InfluxDBClient (
            url=config.get('influx2', 'url'),
            token=config.get('influx2', 'token'),
            org=config.get('influx2', 'org')
        )
        influxdb_write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
        # test more config options and see if they are present
        influxdb_bucket = config.get('influx2', 'bucket')
        influxdb_org = config.get('influx2', 'org')
        _ = config.get('influx2', 'measurement_name')
    except configparser.Error as e:
        logging.error("Config Error: %s", str(e))
        exit(1)
    except ValueError as e:
        logging.error("Config Error: %s", str(e))
        exit(1)

    # create authenticated FB client handler
    fritz_client_auth = None
    request_interval = 10
    try:
        fritz_client_auth = fritzconnection.FritzConnection(
            address=config.get('fritzbox', 'host', fallback='192.168.178.1'),
            port=config.getint('fritzbox', 'port', fallback=49000),
            user=config.get('fritzbox', 'username'),
            password=config.get('fritzbox', 'password'),
            timeout=config.getint('fritzbox', 'timeout', fallback=5),
            use_tls=config.getboolean('fritzbox', 'ssl', fallback=False)
        )

        request_interval = config.getint('fritzbox', 'interval', fallback=10)

    except configparser.Error as e:
        logging.error("Config Error: %s", str(e))
        exit(1)
    except BaseException as e:
        logging.error("Failed to connect to FritzBox '%s'" % str(e))
        exit(1)

    # test connection
    try:
        fritz_client_auth.call_action("DeviceInfo", "GetInfo")
    except fritzconnection.core.exceptions.FritzConnectionException as e:
        if "401" in str(e):
            logging.error("Failed to connect to FritzBox '%s' using credentials. Check username and password!" %
                          config.get('fritzbox', 'host'))
        else:
            logging.error(str(e))

        exit(1)

    logging.info("Successfully connected to FritzBox")

    # read services from config file
    services_to_query = get_services(config, "service")

    logging.info("Starting main loop")

    while running:
        logging.debug("Starting FritzBox requests")

        start = int(datetime.utcnow().timestamp() * 1000)

        # query data
        data = {
            "measurement": config.get('influx2', 'measurement_name'),
            "time": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            #"tags": {"tag1": "abc", "tag2": "def"},
            "fields": query_services(fritz_client_auth, services_to_query)
        }

        logging.debug("Writing data to InfluxDB")

        logging.debug("InfluxDB - measurement: %s" % data.get("measurement"))
        #logging.debug("InfluxDB - time: %s" % data.get("time"))
        for k, v in data.get("fields").items():
            logging.debug(f"InfluxDB - field: {k} = {v}")

        # noinspection PyBroadException
        try:
            influxdb_write_api.write(influxdb_bucket, influxdb_org, data)
        except Exception as e:
            logging.error("Failed to write to InfluxDB <%s>: %s" % (config.get('influx2', 'url'), str(e)))

        duration = int(datetime.utcnow().timestamp() * 1000) - start

        logging.debug("Duration of requesting Fritzbox and sending data to InfluxDB: %0.3fs" % (duration / 1000))

        if duration + 1000 >= (request_interval * 1000):
            logging.warning(f"Request interval of {request_interval} seconds might be to short considering last "
                            "duration for all requests was %0.3f seconds" % (duration / 1000))

        # just sleep for interval seconds - last run duration
        for _ in range(0, int(((request_interval * 1000) - duration) / 100)):
            if running is False:
                break
            time.sleep(0.0965)


if __name__ == "__main__":
    main()
