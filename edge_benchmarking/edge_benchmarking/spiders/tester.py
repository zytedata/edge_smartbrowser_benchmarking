import base64
from copy import deepcopy
import scrapy
import json
from scrapy.utils.response import get_meta_refresh
from edge_benchmarking.spiders import BrowserstackBenchmarkSpider


class TesterSpider(BrowserstackBenchmarkSpider):
    name = 'tester'

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        from_crawler = super(TesterSpider, cls).from_crawler
        spider = from_crawler(crawler, *args, **kwargs)
        # crawler.signals.connect(spider.idle, signal=scrapy.signals.spider_idle)
        return spider

    def idle(self):
        stats = self.response_analyser.get_results_by_parameters()
        self.logger.info(f'AB analyser [parameters]: {json.dumps(stats, indent=4)}')
        impact_stats = self.response_analyser.get_impact_stats()
        self.logger.info(f'AB analyser [impact stats]: {json.dumps(impact_stats, indent=4)}')
        self.crawler.stats.set_value('_impact_stats', impact_stats or "Not Found")

        positive_configs = self.response_analyser.get_best_configs()
        self.logger.info(f'AB analyser [positive configs]: {json.dumps(positive_configs, indent=4)}')

        self.crawler.stats.set_value('_analyser_positive_configs', positive_configs)

        if positive_configs and 'datacenter' in ''.join(positive_configs.keys()):  # Stop for good configs with DC
            return

        suggestion = self.antibot_configurator.get_suggestion()
        self.logger.info(f'AB Analyser tune suggestion: {suggestion}')

        if not self.auto_config or not suggestion:
            return

        self.logger.info('Trying to make start_requests with new suggestion!')
        test_assets = deepcopy(self.default_test_assets)
        test_assets.update(suggestion)
        for x in self.start_requests(test_assets=test_assets):
            self.crawler.engine.crawl(x)

    def make_public_fields(self, item):
        preffix = '_'  # to make items to be public on slack.
        fields = ['title', 'h1', 'response_length',
                  'zyte-edge-peer-id', 'headers']  # to make items to be public on slack.
        for k in fields:
            if item.get(k) is not None:
                item[preffix + k] = item[k]
                del item[k]

    def parse(self, response):
        if self.follow_meta_redirects:
            interval, url = get_meta_refresh(response, [])
            if url:
                self.logger.info(f'META Redirect found, interval: {interval}, url: {url}, response.url: {response.url}')
                self.crawler.stats.inc_value('meta_redirect_found')
                request = scrapy.Request(url, meta={'request': response.meta['request']})
                self.fulfill_request(request)
                yield request
                return

        upstream_response = response.meta.get('crawlera_fetch', {}).get('upstream_response', {}).get('body', {})

        # print("================")
        # print("Response: ", upstream_response)
        if 'zyte-edge-peer-id' in upstream_response.get('headers', [])[0].get('name', ''):
            zyte_edge_peer_id = upstream_response.get('headers', [])[0].get('value', '')

        else:
            zyte_edge_peer_id = None

        # add the count of original status code to the list of status codes
        original_status = self.crawler.stats.inc_value(f"_original_status/{upstream_response.get('original_status')}")
        status = self.crawler.stats.inc_value(f"_status_code/{response.status}")

        item = {
            'response_length': len(response.text),
            'zyte-edge-peer-id': zyte_edge_peer_id,
            'original_status': upstream_response.get('original_status'),
            # 'stats': (upstream_response.get('custom_data') or {}).get('stats'),
            # 'parent_request': response.meta.get('request'),
            'timing': response.meta.get('crawlera_fetch', {}).get('timing', {}).get("latency"),
            # 'download_latency': response.meta.get('download_latency'),
            'status': response.status,
            'url': upstream_response.get('original_url'),
            'headers': upstream_response.get('headers')[1:3],  # remove peer id
        }

        try:
            item["title"] = response.css("title ::text").get()
            item["h1"] = response.css("h1 ::text").get()
        except ValueError:
            pass


        if network_captures := upstream_response.get('networkCapture', []):
            network_capture_urls = [x.get('url') for x in network_captures]
            item['network_capture_urls'] = network_capture_urls
            network_capture = network_captures[0]
            network_capture_body = network_capture.get('body')
            if network_capture_body:
                network_capture_body = base64.b64decode(network_capture_body).decode()
                item['network_capture'] = network_capture_body[:10000]
            if network_capture['request'].get('body'):
                item['network_capture_request_body'] = network_capture['request']['body']

        for name, selector in self.extract_css.items():
            value = response.css(selector).get()
            if value:
                if not item.get('extracted_css'):
                    item['extracted_css'] = {}
                item[name] = ' '.join(value.split())  # to remove extra spaces from css extracted data
                item['extracted_css'][name] = value

        if self.save_body:
            item["body"] = response.text
            if self.save_body > 1:
                item["body"] = item["body"][: self.save_body]

        if screenshot_data := upstream_response.get('screenshot'):
            if self.save_screenshots: # to file
                binary_screenshot_data = base64.b64decode(upstream_response.get('screenshot'))
                if binary_screenshot_data:
                    config_str = self.response_analyser.get_config_string(response)
                    screenshot_name = f"{config_str}_{response.meta['config']['attempt']}"
                    with open(f"./screenshots/{screenshot_name}.jpg", "wb") as file:
                        file.write(binary_screenshot_data)
            else: # to item
                item['screenshot'] = screenshot_data

        if response.status != 200:
            item['error'] = {
                'headers': response.headers.to_unicode_dict(),
                'body': response.text,
                'uncork_error': upstream_response.get('error')
            }
        if usage := upstream_response.get('usage'):
            self.crawler.stats.inc_value('requests_datacenter', usage['smartBrowser']['dataCenterProxyRequests'])
            self.crawler.stats.inc_value('requests_residential', usage['smartBrowser']['residentialProxyRequests'])

        if headers := (upstream_response.get('custom_data') or {}).get('applied_headers'):
            item['applied_headers'] = headers

        # short_config = response.meta['config']['short_config']
        # str_config = self.response_analyser.get_config_string(response)
        # item['config'] = short_config
        # antibot_sign = f"{self.response_analyser.get_result_string(response)}"
        # self.crawler.stats.inc_value(f'_antibot_found/{antibot_sign}')
        # self.crawler.stats.inc_value(f'~config/{str_config}/{antibot_sign}')
        # item['antibot_sign'] = antibot_sign

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
            if debug_output.get('captcha_solver_result') and debug_output.get('captcha_solver_result', {}).get('captchaFound'):
                self.crawler.stats.inc_value('captcha_found')
                if debug_output['captcha_solver_result'].get('success'):
                    self.crawler.stats.inc_value('captcha_solved')

                item['captcha_info'] = debug_output['captcha_solver_result']

            if debug_output["har"] and debug_output["har"]["log"]["entries"]:
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

            har = debug_output.get('har', {})
            if har:
                har_entries = har.get('log', {}).get('entries', [])
                if len(har_entries) > 1:
                    har_cookies = har_entries[1].get('request', {}).get('cookies')
                    if har_cookies:
                        for cookie in har_cookies:
                            if cookie.get('name') == 'SG_SS':
                                print(f"SG_SS: --->>>> {cookie.get('value')}")
                                ua = [x for x in har_entries[1].get('request', {}).get('headers') if
                                      x.get('name').lower() == 'user-agent'][0].get('value')
                                data = {
                                    'ua': ua,
                                    'sg_ss': cookie.get('value')
                                }
                                print(data)
                                item['google_cookies_data'] = data
                                break

        self.make_public_fields(item)




        yield item

        # self.response_analyser.log_result(response)
