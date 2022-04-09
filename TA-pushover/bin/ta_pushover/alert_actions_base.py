""" alert actions base """

# pylint: disable=wrong-import-position,wrong-import-order

from __future__ import print_function
from builtins import str
import csv
import gzip
import sys
from traceback import format_exc

from httplib2 import (socks, ProxyInfo, Http)

try:
    from splunk.clilib.bundle_paths import make_splunkhome_path
except ImportError:
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

# TODO: How does it depend on CIM module?
sys.path.insert(0, make_splunkhome_path(["etc", "apps", "Splunk_SA_CIM", "lib"]))

from .cim_actions import ModularAction
from .logging_helper import get_logger
import logging
from .aob_py3.splunk_aoblib.rest_helper import TARestHelper
from .aob_py3.splunk_aoblib.setup_util import Setup_Util

class ModularAlertBase(ModularAction):
    """ modular alert """
    def __init__(self, ta_name, alert_name):
        self._alert_name = alert_name
        # self._logger_name = "modalert_" + alert_name
        self._logger_name = alert_name + "_modalert"
        self._logger = get_logger(self._logger_name)
        super(ModularAlertBase, self).__init__(
            sys.stdin.read(), self._logger, alert_name)
        self.setup_util_module = None
        self.setup_util = None
        self.result_handle = None
        self.ta_name = ta_name
        self.splunk_uri = self.settings.get('server_uri')
        self.setup_util = Setup_Util(self.splunk_uri, self.session_key, self._logger)

        self.rest_helper = TARestHelper(self._logger)

    def log_error(self, msg):
        """ log an error """
        self.message(msg, 'failure', level=logging.ERROR)

    def log_info(self, msg):
        """ info level message """
        self.message(msg, 'success', level=logging.INFO)

    def log_debug(self, msg):
        """ debug log """
        self.message(msg, None, level=logging.DEBUG)

    def log_warn(self, msg):
        """ log a warning """
        self.message(msg, None, level=logging.WARN)

    def set_log_level(self, level):
        """ log configurator """
        self._logger.setLevel(level)

    def get_param(self, param_name):
        """ config getter """
        return self.configuration.get(param_name)

    def get_global_setting(self, var_name):
        """ setting getter """
        return self.setup_util.get_customized_setting(var_name)

    def get_user_credential(self, username):
        '''
        if the username exists, return
        {
            "username": username,
            "password": credential
        }
        '''
        return self.setup_util.get_credential_by_username(username)

    @property
    def log_level(self):
        """ welp """
        return self.get_log_level()

    @property
    def proxy(self):
        """ this is so java """
        return self.get_proxy()

    def get_log_level(self):
        """ blep """
        return self.setup_util.get_log_level()

    def get_proxy(self):
        ''' if the proxy setting is set. return a dict like
        {
        proxy_url: ... ,
        proxy_port: ... ,
        proxy_username: ... ,
        proxy_password: ... ,
        proxy_type: ... ,
        proxy_rdns: ...
        }
        '''
        return self.setup_util.get_proxy_settings()

    def _get_proxy_uri(self):
        uri = None
        proxy = self.get_proxy()
        if proxy and proxy.get('proxy_url') and proxy.get('proxy_type'):
            uri = proxy['proxy_url']
            if "proxy_port" in proxy:
                uri = f"{uri}:{proxy['proxy_port']}"
            if "proxy_username" in proxy and proxy.get('proxy_password'):
                uri = f"{proxy['proxy_type']}://{proxy['proxy_username']}:{proxy['proxy_password']}@{uri}/"
            else:
                uri = f"{proxy['proxy_type']}://{uri}"
        return uri

    def send_http_request(
        self,
        url,
        method,
        parameters=None,
        payload=None,
        headers=None,
        cookies=None,
        verify=True,
        cert=None,
        timeout=None,
        use_proxy=True,
        ):
        """ request sender """
        return self.rest_helper.send_http_request(
            url=url,
            method=method,
            parameters=parameters,
            payload=payload,
            headers=headers,
            cookies=cookies,
            verify=verify,
            cert=cert,
            timeout=timeout,
            proxy_uri=self._get_proxy_uri() if use_proxy else None,
        )

    def build_http_connection(
        self,
        config,
        timeout=30,
        disable_ssl_validation=False,
        ):
        """ connection builder """
        # :config: dict like, proxy and account information are in the following
        #         format {
        #             "username": xx,
        #             "password": yy,
        #             "proxy_url": zz,
        #             "proxy_port": aa,
        #             "proxy_username": bb,
        #             "proxy_password": cc,
        #             "proxy_type": http,http_no_tunnel,sock4,sock5,
        #             "proxy_rdns": 0 or 1,
        #         }
        # :return: Http2.Http object
        if not config:
            config = {}

        proxy_type_to_code = {
            "http": socks.PROXY_TYPE_HTTP,
            "http_no_tunnel": socks.PROXY_TYPE_HTTP_NO_TUNNEL,
            "socks4": socks.PROXY_TYPE_SOCKS4,
            "socks5": socks.PROXY_TYPE_SOCKS5,
        }
        if config.get("proxy_type") in proxy_type_to_code:
            proxy_type = proxy_type_to_code[config["proxy_type"]]
        else:
            proxy_type = socks.PROXY_TYPE_HTTP

        rdns = config.get("proxy_rdns")

        proxy_info = None
        if config.get("proxy_url") and config.get("proxy_port"):
            if config.get("proxy_username") and config.get("proxy_password"):
                proxy_info = ProxyInfo(proxy_type=proxy_type,
                                       proxy_host=config["proxy_url"],
                                       proxy_port=int(config["proxy_port"]),
                                       proxy_user=config["proxy_username"],
                                       proxy_pass=config["proxy_password"],
                                       proxy_rdns=rdns)
            else:
                proxy_info = ProxyInfo(proxy_type=proxy_type,
                                       proxy_host=config["proxy_url"],
                                       proxy_port=int(config["proxy_port"]),
                                       proxy_rdns=rdns)
        if proxy_info:
            http = Http(proxy_info=proxy_info, timeout=timeout,
                        disable_ssl_certificate_validation=disable_ssl_validation)
        else:
            http = Http(timeout=timeout,
                        disable_ssl_certificate_validation=disable_ssl_validation)

        if config.get("username") and config.get("password"):
            http.add_credentials(config["username"], config["password"])
        return http

    def process_event(self, *args, **kwargs):
        """ event handler, not needed """
        raise NotImplementedError()

    def pre_handle(self, num, result):
        """ before things get handled, I guess?"""
        result.setdefault('rid', str(num))
        self.update(result)
        return result

    def get_events(self):
        """ does what it says on the name"""
        try:
            try:
                self.result_handle = gzip.open(self.results_file, 'rt')
            except ValueError: # Workaround for Python 2.7 on Windows
                self.result_handle = gzip.open(self.results_file, 'r')
            return (self.pre_handle(num, result) for num, result in enumerate(csv.DictReader(self.result_handle)))
        except IOError:
            msg = "Error: {}."
            self.log_error(msg.format("No search result. Cannot send alert action."))
            sys.exit(2)

    def prepare_meta_for_cam(self):
        """ not even sure """
        try:
            try:
                file_handle = gzip.open(self.results_file, 'rt')
            except ValueError: # Workaround for Python 2.7 on Windows
                file_handle = gzip.open(self.results_file, 'r')
            for num, result in enumerate(csv.DictReader(file_handle)):
                result.setdefault('rid', str(num))
                self.update(result)
                self.invoke()
                break
        finally:
            if file_handle:
                file_handle.close()

    def run(self, argv):
        """ runner """
        status = 0
        if len(argv) < 2 or argv[1] != "--execute":
            msg = f'Error: argv="{argv}", expected="--execute"'
            print(msg, file=sys.stderr)
            sys.exit(1)

        # prepare meta first for permission lack error handling: TAB-2455
        self.prepare_meta_for_cam()
        try:
            level = self.get_log_level()
            if level:
                self._logger.setLevel(level)
        except Exception as error: # pylint: disable=broad-except
            if error and '403' in str(error):
                self.log_error('User does not have permissions')
            else:
                self.log_error('Unable to set log level')
            sys.exit(2)

        try:
            status = self.process_event()
        except IOError:
            msg = "Error: {}."
            self.log_error(msg.format("No search result. Cannot send alert action."))
            sys.exit(2)
        except Exception as error: #pylint: disable=broad-except
            msg = "Unexpected error: {}."
            if error:
                self.log_error(msg.format(str(error)))
            else:
                self.log_error(msg.format(format_exc()))
            sys.exit(2)
        finally:
            if self.result_handle:
                self.result_handle.close()

        return status
