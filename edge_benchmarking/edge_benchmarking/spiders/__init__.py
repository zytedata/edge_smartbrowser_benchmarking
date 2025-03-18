# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.
import base64
import json
import re
import time
import os
import uuid
from copy import deepcopy
from urllib.parse import urlparse

import scrapy
from scrapinghub import ScrapinghubClient
from scrapy.utils.response import get_meta_refresh

# from browserstack_benchmark.generator import Generator
# from browserstack_benchmark.analyser import Analyser
# from browserstack_benchmark.configurator import Configurator

SESSION_UID = str(uuid.uuid4())


class BrowserstackBenchmarkSpider(scrapy.Spider):
    crawlera_enabled = False
    zyte_smartproxy_enabled = False
    crawlera_fetch_enabled = True
    log_fulfill_request = False

    sessions_strings = []

    default_test_assets = {}  # it has ignore_ban, ignore_ccm, disable session if self.use_ccm = false (default)
    # to Add server_log, browserless_log ???

    default_fetch_args = {
        "headers": [],
        "cookies": [],
        "debug": True,
        "debug_options": {
            "browserless_log": True,
            "server_log": True,
            "use_edge": True
        }
    }

    results = {}

    # antibot_configurator = Configurator()
    # response_analyser = Analyser(antibot_configurator)

    @classmethod
    def update_settings(cls, settings):
        super().update_settings(settings)
        cls.set_fetch_credentials(settings)

    def set_fetch_credentials(settings):
        fetch_enpoint_suffix = (
            settings["CRAWLERA_FETCH_URL"].split(".")[0].split("/")[-1].replace("-", "_")
        )
        settings["CRAWLERA_FETCH_APIKEY"] = settings[
            f"CRAWLERA_FETCH_APIKEY_{fetch_enpoint_suffix.upper()}"
        ]
        settings["CRAWLERA_FETCH_APIPASS"] = settings[
            f"CRAWLERA_FETCH_APIPASS_{fetch_enpoint_suffix.upper()}"
        ]

        if not settings["CRAWLERA_FETCH_APIKEY"]:
            settings["CRAWLERA_FETCH_APIKEY"] = settings["CRAWLERA_FETCH_APIKEY_DEVELOP"]
            settings["CRAWLERA_FETCH_APIPASS"] = settings["CRAWLERA_FETCH_APIPASS_DEVELOP"]

        if ".dev02-api" in settings["CRAWLERA_FETCH_URL"]:
            settings["CRAWLERA_FETCH_APIKEY"] = settings["CRAWLERA_FETCH_APIKEY_DEV_API"]
            settings["CRAWLERA_FETCH_APIPASS"] = settings["CRAWLERA_FETCH_APIPASS_DEV_API"]

        if "prod-green.zsb01-api" in settings["CRAWLERA_FETCH_URL"]:
            settings["CRAWLERA_FETCH_APIKEY"] = settings["CRAWLERA_FETCH_APIKEY_PROD_API"]
            settings["CRAWLERA_FETCH_APIPASS"] = settings["CRAWLERA_FETCH_APIPASS_PROD_API"]

        if "prod.uncork.zyte.group" in settings["CRAWLERA_FETCH_URL"]:
            settings["CRAWLERA_FETCH_APIKEY"] = settings["CRAWLERA_FETCH_APIKEY_PROD_API"]
            settings["CRAWLERA_FETCH_APIPASS"] = settings["CRAWLERA_FETCH_APIPASS_PROD_API"]

        if "test02.gcp" in settings["CRAWLERA_FETCH_URL"]:
            settings["CRAWLERA_FETCH_APIKEY"] = settings["CRAWLERA_FETCH_APIKEY_DEVELOP"]
            settings["CRAWLERA_FETCH_APIPASS"] = settings["CRAWLERA_FETCH_APIPASS_DEVELOP"]

    def __init__(self, *args, **kwargs):
        super(BrowserstackBenchmarkSpider, self).__init__(*args, **kwargs)
        self.started_job_id = os.environ.get('SCRAPY_JOB') or f"evgeny/{str(time.time()).split('.')[0]}"
        self.logger.info(f'Started job: {self.started_job_id}')

        if kwargs.get("extra_args") is not None:
            self.default_fetch_args.update(json.loads(kwargs.get("extra_args")))

        if kwargs.get("debug_args") is not None:
            self.default_fetch_args['debug_options'].update(json.loads(kwargs.get("debug_args")))

        self.use_ccm = bool(int(kwargs.get("use_ccm", "1")))
        if not self.use_ccm:
            for x in ['ignore_ban', 'ignore_ccm', 'disable_session']:
                self.default_test_assets[x] = [True]

        if kwargs.get("ignore_ban") is not None:
            self.ignore_ban = bool(int(kwargs.get("ignore_ban", "0")))
            self.default_test_assets['ignore_ban'] = self.ignore_ban

        if kwargs.get("disable_session") is not None:
            self.disable_session = bool(int(kwargs.get("disable_session", "0")))
            self.default_test_assets['disable_session'] = self.disable_session

        self.input_job_id = kwargs.get("job_id")
        self.load_urls_func = self.load_urls

        self.requests_multiplier = int(kwargs.get('requests_multiplier', '0'))

        self.requests_limit = int(kwargs.get('limit', 10))

        # if self.requests_multiplier:
        #     self.requests_limit = self.requests_multiplier

        self.urls_template = kwargs.get("url_template", "")  # For loading from job_id

        self.save_body = int(kwargs.get("save_body", "0"))

        self.extract_css = json.loads(kwargs.get("extract_css", "{}"))

        self.network_capture = json.loads(kwargs.get("network_capture", "{}"))

        self.locale = kwargs.get("locale")  # To move

        self.fetch_endpoint = kwargs.get("fetch_endpoint")

        self.use_edge = bool(int(kwargs.get("use_edge", "0")))

        self.follow_meta_redirects = bool(kwargs.get("follow_meta_redirects"))

        self.screenshots_to_item = bool(int(kwargs.get('show_screenshots', '0')))

        self.session_context = kwargs.get("session_context")

        self.session_context_params = kwargs.get("session_context_params")
        self.mix_session_context = bool(int(kwargs.get("mix_session_context", "0")))

        self.user_agent = kwargs.get("user_agent")
        self.headers = kwargs.get("headers")
        self.cookies = kwargs.get("cookies")

        self.url = kwargs.get("url")

        # set default params [should work with coping from IDE]
        ide_url = kwargs.get("ide_url")
        if ide_url:
            ide_json = base64.b64decode(ide_url.split('#api-debugger/')[1]).decode("utf-8")
            self.translate_ide_json(ide_json)

        ide_json = kwargs.get("ide_json")
        if ide_json:
            self.translate_ide_json(ide_json)

        # FROM TESTER

        self.config = json.loads(kwargs.get("config", "{}"))
        if self.config:
            self.default_test_assets.update(self.config)

        self.auto_config = False  # disabled by default

        if 'auto_config' in kwargs:  # override auto_config if it's set
            self.auto_config = bool(int(kwargs['auto_config']))
            if self.input_job_id or self.config:  # disable if job_id or config is set
                self.logger.warning('Disabling auto config because input_job_id OR config exists')
                self.auto_config = False
            if self.auto_config:  # By default for each 'ignore_ban','ignore_ccm','disable_session' -> True
                # to add this to readme
                for x in ['ignore_ban', 'ignore_ccm', 'disable_session']:
                    if kwargs.get(x) is None:
                        self.default_test_assets[x] = [True]
                if self.requests_limit > 50:
                    self.requests_limit = 50
                    self.logger.warning('Reducing requests_limit to 50 because of auto_config')

        self.save_screenshots = bool(int(kwargs.get("save_screenshots", "0"))) and not os.environ.get("SCRAPY_JOB")

    def fulfill_request(self, request, config={}):
        request.dont_filter = True

        if self.crawlera_fetch_enabled:
            request.meta["crawlera_fetch"] = {
                "args": deepcopy(self.default_fetch_args),
            }

            request.meta["crawlera_fetch"]["args"]["job_id"] = self.started_job_id

            # TODO: Move all rest params to `generator.py` and use via argument `config`

            if self.mix_session_context:
                request.meta["crawlera_fetch"]["args"]['session_context'] = [{"name": "42", "value": "42"}]
                request.meta["crawlera_fetch"]["args"]['session_context_parameters'] = {
                    "actions": [{"action": "waitForTimeout", "timeout": 5, "onError": "return"}]
                }

            if self.session_context:
                request.meta["crawlera_fetch"]["args"]["session_context"] = json.loads(self.session_context)
            if self.session_context_params:
                request.meta["crawlera_fetch"]["args"]["session_context_parameters"] = json.loads(
                    self.session_context_params
                )

            if self.user_agent:
                # request.meta['crawlera_fetch']['args']['headers'].append(
                #     {"name": "User-Agent", "value": self.user_agent}
                # )
                request.meta['crawlera_fetch']['args']['user_agent'] = self.user_agent

            if self.headers:
                # to fix!
                # request.meta['crawlera_fetch']['args']['headers'].append(
                #     {"name": "User-Agent", "value": self.user_agent}
                # )
                request.meta['crawlera_fetch']['args']['headers'] += json.loads(self.headers)

            if self.cookies:
                request.meta['crawlera_fetch']['args']['cookies'] += json.loads(self.cookies)

            if self.use_edge:
                request.meta['crawlera_fetch']['args']['debug_options']['use_edge'] = True

            if self.network_capture:
                request.meta["crawlera_fetch"]["args"]["networkCapture"] = self.network_capture

            if self.locale:
                lang_headers = [
                    x
                    for x in request.meta["crawlera_fetch"]["args"].get("headers", [])
                    if x["name"].lower() == "accept-language"
                ]
                if lang_headers:
                    lang_headers[0]["value"] = self.locale
                else:
                    request.meta["crawlera_fetch"]["args"]["headers"].append(
                        {"name": "accept-language", "value": self.locale}
                    )

            # if (self.save_screenshots or self.screenshots_to_item) and config['fetch_config'].get('render'):
            # if config['fetch_config'].get('render'):  # to test screenshots for all cases!
            #     request.meta["crawlera_fetch"]["args"]["screenshot"] = True
            #     request.meta["crawlera_fetch"]["args"]["screenshot_options"] = {
            #         "full_page": True
            #     }

            request.headers["X-Zyte-Org"] = "3"
            request.headers["X-Zyte-User"] = "30"
            request.headers["x-verbose-logging"] = True

            # \"session\": {\"id\": \"$(uuidgen)\"}
            # request.meta["crawlera_fetch"]["args"]["session"] = {"id": str(uuid.uuid4())}
            # request.meta["crawlera_fetch"]["args"]["session"] = {"id": SESSION_UID}

    def recursive_update_in_place(self, original: dict, updates: dict) -> None:
        for key, value in updates.items():
            if isinstance(value, dict) and key in original and isinstance(original[key], dict):
                self.recursive_update_in_place(original[key], value)
            else:
                original[key] = value

    def translate_ide_json(self, json_str):
        default_fetch_args = json.loads(json_str)
        self.default_fetch_args.update(default_fetch_args)
        # translate from ZAPI to Uncork-Server API
        self.default_fetch_args.pop("requestBuildMode", None)
        self.default_fetch_args.pop("experimental", None)

        if self.default_fetch_args.get('geolocation'):
            self.default_fetch_args['region'] = self.default_fetch_args.get('geolocation')
            del self.default_fetch_args['geolocation']

        if self.default_fetch_args.get('httpResponseBody'):
            self.default_fetch_args['render'] = not self.default_fetch_args['httpResponseBody']
            del self.default_fetch_args['httpResponseBody']

        if self.default_fetch_args.get('httpRequestMethod'):
            self.default_fetch_args['method'] = self.default_fetch_args['httpRequestMethod'].lower()
            del self.default_fetch_args['httpRequestMethod']

        if self.default_fetch_args.get('httpRequestText'):
            body = base64.b64encode(self.default_fetch_args['httpRequestText'].encode()).decode("utf-8")
            self.default_fetch_args['body'] = body
            del self.default_fetch_args['httpRequestText']

        if self.default_fetch_args.get('httpRequestBody'):
            body = self.default_fetch_args['httpRequestBody']
            self.default_fetch_args['body'] = body
            del self.default_fetch_args['httpRequestBody']

        if self.default_fetch_args.get('browserHtml'):
            self.default_fetch_args['render'] = self.default_fetch_args['browserHtml']
            del self.default_fetch_args['browserHtml']

        if screenshot_options := self.default_fetch_args.get('screenshotOptions'):
            self.default_fetch_args['screenshot_options'] = screenshot_options
            del self.default_fetch_args['screenshotOptions']
            if screenshot_options.get('fullPage'):
                screenshot_options['full_page'] = screenshot_options['fullPage']
                del screenshot_options['fullPage']

        if request_headers := self.default_fetch_args.get('requestHeaders'):
            if request_headers.get('referer'):
                self.default_fetch_args['referer'] = request_headers['referer']
                del request_headers['referer']
            for k, v in request_headers.items():
                self.default_fetch_args['headers'].append({"name": k, "value": v})
            del self.default_fetch_args['requestHeaders']

        if self.default_fetch_args.get('customHttpRequestHeaders'):
            self.default_fetch_args['headers'].extend(self.default_fetch_args['customHttpRequestHeaders'])
            del self.default_fetch_args['customHttpRequestHeaders']

        if self.default_fetch_args.get('sessionContext'):
            self.default_fetch_args['session_context'] = self.default_fetch_args['sessionContext']
            del self.default_fetch_args['sessionContext']

        if self.default_fetch_args.get('sessionContextParameters'):
            self.default_fetch_args['session_context_parameters'] = self.default_fetch_args['sessionContextParameters']
            del self.default_fetch_args['sessionContextParameters']

        if self.default_fetch_args.get('networkCapture'):
            for x in self.default_fetch_args.get('networkCapture'):
                x['deliverBody'] = x['httpResponseBody']
                del x['httpResponseBody']

        if self.default_fetch_args.get('_smartBrowserFeatures'):
            self.default_fetch_args['debug_options'].update(self.default_fetch_args['_smartBrowserFeatures'])
            del self.default_fetch_args['_smartBrowserFeatures']

        if not self.url:
            self.url = self.default_fetch_args.get("url")

        print(self.default_fetch_args)

    def load_urls(self):
        sh_apikey = self.settings.get("SH_API_KEY")
        if not sh_apikey:
            print("Missed SH_API_KEY")
            return []

        client = ScrapinghubClient(sh_apikey)
        job = client.get_job(self.input_job_id)

        api_items_limit = (
                self.settings.get("API_ITEMS_LIMIT") or self.requests_limit * 2
        )
        if api_items_limit < 100:
            api_items_limit *= 5
        reqs = []
        for reqitem in job.requests.iter(count=api_items_limit):
            if self.urls_template and not re.search(self.urls_template, reqitem["url"]):
                continue
            reqs.append(reqitem)
            if len(reqs) > self.requests_limit:
                break

        reqs = reqs[: self.requests_limit] * (self.requests_multiplier or 1)

        return [x['url'] for x in reqs]
        # return [
        #     scrapy.Request(self.goto_before or req["url"], meta={"request": req})
        #     for req in reqs
        # ]

    def start_requests(self, test_assets={}):
        if self.input_job_id:
            urls = self.load_urls()
        else:
            urls = [self.url] * self.requests_limit

        test_assets.update(self.default_test_assets)

        # x = Generator(deepcopy(test_assets), urls[0], self.logger)
        # configs = x.gen()

        requests = []
        for i in range(len(urls)):
            # for config in configs:
            r = scrapy.Request(urls[i])
            r.meta['requested_url'] = urls[i]
            self.fulfill_request(r)
            # self.recursive_update_in_place(r.meta['crawlera_fetch']['args'], config['fetch_config'])
            self.logger.debug(f'Attempt: {i}')
            # config['attempt'] = i
            # r.meta['config'] = deepcopy(config)
            requests.append(r)

            if not self.log_fulfill_request and self.crawlera_fetch_enabled:
                self.log_fulfill_request = True
                self.logger.info('Crawlera fetch args: ' + json.dumps(r.meta['crawlera_fetch'], indent=4))

        self.logger.info(f'Prepared {len(requests)} requests')

        for request in requests:
            yield request

    def parse(self, response):
        if self.follow_meta_redirects:
            interval, url = get_meta_refresh(response, [])
            if url:
                self.logger.info(
                    f"META Redirect found, interval: {interval}, url: {url}, response.url: {response.url}"
                )
                self.crawler.stats.inc_value("meta_redirect_found")
                request = scrapy.Request(
                    url, meta={"request": response.meta["request"]}
                )
                self.fulfill_request(request)
                yield request
                return

        upstream_response = (
            response.meta.get("crawlera_fetch", {})
            .get("upstream_response", {})
            .get("body", {})
        )
        item = {
            "response_length": len(response.text),
            "id": upstream_response.get("id"),
            "usage": upstream_response.get("usage"),
            "usage_v2": upstream_response.get("usage_v2"),
            "actions": upstream_response.get("actions"),
            "cookies": upstream_response.get("cookies"),
            "stats": (upstream_response.get("custom_data") or {}).get("stats"),
            "parent_request": response.meta.get("request"),
            "timing": response.meta.get("crawlera_fetch", {})
            .get("timing", {})
            .get("latency"),
            "download_latency": response.meta.get("download_latency"),
            "status": response.status,
            "url": response.url,
            "requested_url": response.meta['requested_url'],
        }

        try:
            item["title"] = response.css("title ::text").get()
            item["h1"] = response.css("h1 ::text").get()
        except ValueError:
            pass

        if not item.get("h1"):
            self.crawler.stats.inc_value("no_h1")

        if screenshot := upstream_response.get("screenshot"):
            item["screenshot"] = screenshot
            binary_screenshot_data = base64.b64decode(
                upstream_response.get("screenshot")
            )
            if binary_screenshot_data and self.save_screenshots:
                screenshot_name = f"screenshot_{self.cnt}"
                self.cnt += 1
                with open(
                        f"./screenshots/{screenshot_name.replace('/', '|')}.jpg", "wb"
                ) as file:
                    file.write(binary_screenshot_data)

        if self.crawlera_fetch_enabled:
            uas = [
                x["value"]
                for x in response.meta["crawlera_fetch"]["args"]["headers"]
                if x["name"].lower() == "user-agent"
            ]
            item["ua"] = uas[0] if uas else ""
            self.crawler.stats.inc_value(f"profiles/{item['ua']}/{response.status}")

        for name, selector in self.extract_css.items():
            item[name] = response.css(selector).get()
        if self.save_body:
            item["body"] = response.text
            if self.save_body > 1:
                item["body"] = item["body"][: self.save_body]
        if self.screenshots_to_item:
            item['screenshot'] = upstream_response.get('screenshot')
        if response.status not in [200, 404]:
            item["error"] = {
                "headers": response.headers.to_unicode_dict(),
                "body": response.text,
                "uncork_error": upstream_response.get("error"),
            }
        if usage := upstream_response.get("usage"):
            self.crawler.stats.inc_value(
                "requests_datacenter", usage["smartBrowser"]["dataCenterProxyRequests"]
            )
            self.crawler.stats.inc_value(
                "requests_residential",
                usage["smartBrowser"]["residentialProxyRequests"],
            )

        if usage2 := upstream_response.get("usage_v2"):
            self.crawler.stats.inc_value(
                "requests_raw", usage2["smartBrowser"]["features"]["rawHtmlDownload"]
            )
            self.crawler.stats.inc_value(
                "requests_render",
                usage2["smartBrowser"]["features"]["renderedHtmlDownload"],
            )

        if headers := (upstream_response.get("custom_data") or {}).get(
                "applied_headers"
        ):
            item["applied_headers"] = headers

        debug_output = upstream_response.get("debug_output")
        if debug_output:
            item["logs"] = debug_output["logs"]
            item["non_intercepted_requests"] = debug_output.get(
                "non_intercepted_requests"
            )
            item["intercepted_requests"] = debug_output.get("intercepted_requests")

            item["stats"] = debug_output.get("stats")

            item["proxy_server"] = debug_output["stats"]["proxy_server_address"]
            item["proxy_username"] = debug_output["stats"]["proxy_username"]
            item["session_string"] = f"{item['proxy_username']}@{item['proxy_server']}"

            item["cookies"] = upstream_response.get("cookies")

            item['captcha_solver_result'] = debug_output['captcha_solver_result']
            if debug_output['captcha_solver_result'].get('captchaFound'):
                self.crawler.stats.inc_value('captcha_found')
                if debug_output['captcha_solver_result'].get('success'):
                    self.crawler.stats.inc_value('captcha_solved')

            if debug_output["har"]:
                item["har_initial_headers"] = debug_output["har"]["log"]["entries"][0][
                    "request"
                ]["headers"]
                item["har_initial_status"] = debug_output["har"]["log"]["entries"][0][
                    "response"
                ]["status"]
                item["har_initial_ua"] = [
                    x["value"]
                    for x in item["har_initial_headers"]
                    if x["name"] == "User-Agent"
                ]

                har_codes = [
                    x["response"]["status"]
                    for x in debug_output["har"]["log"]["entries"]
                    if x["request"]["url"] == response.url
                ]
                item["har_codes"] = har_codes
                if 200 in har_codes and (403 in har_codes or 307 in har_codes):
                    item["_challenge_solved"] = True
                    self.crawler.stats.inc_value("_challenge_solved")

            if item["session_string"] not in self.sessions_strings:
                self.sessions_strings.append(item["session_string"])
                self.crawler.stats.inc_value("_sessions_unique")

            # self.crawler.stats.inc_value(f"proxy_server_ip/{item['proxy_server']}")
            proxy_status_key = (
                f"proxy_server_ip_history_initial/{item['session_string']}"
            )
            if item.get("har_initial_status"):
                statuses_per_proxy = (
                        self.crawler.stats.get_value(proxy_status_key, "")
                        + f"{item['har_initial_status']},"
                )
                self.crawler.stats.set_value(proxy_status_key, statuses_per_proxy)
                self.crawler.stats.inc_value(
                    f"proxy_har_initial_status/{item['har_initial_status']}"
                )

            proxy_status_key = f"proxy_server_ip_history/{item['session_string']}"
            statuses_per_proxy = (
                    self.crawler.stats.get_value(proxy_status_key, "")
                    + f"{response.status},"
            )
            self.crawler.stats.set_value(proxy_status_key, statuses_per_proxy)
            self.crawler.stats.inc_value(f"proxy_status/{response.status}")

        if (
                response.status != 200
                or not item.get('h1')
        ):
            if response.status != 200:
                err = str(response.status)
            elif not item.get("h1"):
                err = "no_h1"
            else:
                err = "unknown"
            self.crawler.stats.inc_value(f"error/{err}")
            item[f"error_{err}"] = True
        else:
            self.crawler.stats.inc_value("__SUCCESS")
            item["success"] = True

        yield item
