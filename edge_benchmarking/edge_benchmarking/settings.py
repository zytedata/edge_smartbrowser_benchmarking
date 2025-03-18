# Scrapy settings for browserstack_benchmark project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

CRAWLERA_FETCH_APIKEY = None
CRAWLERA_FETCH_APIPASS = None
SH_API_KEY = None
CRAWLERA_APIKEY = None
# Set API keys from setting_local.py

try:
    from edge_benchmarking.settings_local import *
except ModuleNotFoundError:
    print("Local settings import error")

BOT_NAME = "edge_benchmarking"

SPIDER_MODULES = ["edge_benchmarking.spiders"]
NEWSPIDER_MODULE = "edge_benchmarking.spiders"

CRAWLERA_FETCH_ENABLED = True

CRAWLERA_URL = "http://cm-23.scrapinghub.com:8010"

# CRAWLERA_FETCH_URL = 'https://cm-58.scrapinghub.com:8014/fetch/v2'

# CRAWLERA_FETCH_URL = 'https://profiles-prod.zsb01-api.gcp.uncork.zyte.group/v2/fetch'

# CRAWLERA_FETCH_URL = 'https://abtest.test02.gcp.uncork.zyte.group/v2/fetch'
# CRAWLERA_FETCH_URL = 'https://api.prod02.gcp.uncork.zyte.group/v2/fetch'

# CRAWLERA_FETCH_URL = 'https://crawlera.prod.uncork.zyte.group/v2/fetch'

# CRAWLERA_FETCH_URL = 'https://prod-green.zsb01-api.gcp.uncork.zyte.group/v2/fetch'

# CRAWLERA_FETCH_URL = 'https://zde.prod.uncork.zyte.group/v2/fetch'

CRAWLERA_FETCH_URL = 'https://zapi-edge-prototype.dev02-api.gcp.uncork.zyte.group/v2/fetch'

# CRAWLERA_FETCH_URL = 'https://ddx---headless-test-o7sg27rnya-uc.a.run.app/direct'

# CRAWLERA_FETCH_URL = "https://develop.dev02-api.gcp.uncork.zyte.group/v2/fetch"

# CRAWLERA_FETCH_URL = "https://api.pre01-api.gcp.api.zyte.group/v2/fetch"

# CRAWLERA_FETCH_URL = 'https://sessions-api.dev02-api.gcp.uncork.zyte.group/v2/fetch'

# CRAWLERA_FETCH_URL = 'https://fix-accept-language-logic.dev02-api.gcp.uncork.zyte.group/v2/fetch'

# CRAWLERA_FETCH_URL = 'https://develop.test02.gcp.uncork.zyte.group/v2/fetch'   !!! PYTHON!!!!!
# 'https://stockx.com/air-jordan-4-retro-se-craft-photon-dust'

# CRAWLERA_FETCH_URL = 'https://instagram-cookie-fix.dev02-api.gcp.uncork.zyte.group/v2/fetch'

# CRAWLERA_FETCH_URL = 'https://crawlera-profiles-experimental.test02.gcp.uncork.zyte.group/v2/fetch'
# CRAWLERA_FETCH_URL = 'https://sahibinden.test02.gcp.uncork.zyte.group/v2/fetch'

CRAWLERA_FETCH_RAISE_ON_ERROR = False

CRAWLERA_DEFAULT_HEADERS = {
    "X-Crawlera-Profile": "desktop",
    "X-Crawlera-Cookies": "disable",
    # 'X-Crawlera-Wait': 0,
}

API_ITEMS_LIMIT = 0
BIGQUERY_MAX_LIMIT = 100000

# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = 'browserstack_benchmark (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False
COOKIES_ENABLED = True
RETRY_ENABLED = False
HTTPERROR_ALLOW_ALL = True

METAREFRESH_ENABLED = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
# CONCURRENT_REQUESTS = 4

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY = 0.5
# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 32

# CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
# COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
# DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
# }

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
# SPIDER_MIDDLEWARES = {
#    'browserstack_benchmark.middlewares.BrowserstackBenchmarkSpiderMiddleware': 543,
# }

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
# DOWNLOADER_MIDDLEWARES = {
#    'browserstack_benchmark.middlewares.BrowserstackBenchmarkDownloaderMiddleware': 543,
# }

DOWNLOADER_MIDDLEWARES = {
    "scrapy_crawlera.CrawleraMiddleware": 300,
    "crawlera_fetch.CrawleraFetchMiddleware": 585,
    "scrapy_zyte_smartproxy.ZyteSmartProxyMiddleware": 610,
}

# Enable Scrapy Zyte Smart Proxy to interact with Zyte Smart Proxy Manager
ZYTE_SMARTPROXY_ENABLED = False
ZYTE_SMARTPROXY_APIKEY = "apikey"

# Set Zyte Smart Proxy Manager proxy
ZYTE_SMARTPROXY_URL = "http://zyte-proxy-develop.dev02-api.gcp.uncork.zyte.group:8011"

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    # "scrapy.pipelines.images.ImagesPipeline": 1
    # 'browserstack_benchmark.pipelines.GCPStorePipeline': 300,
}

IMAGES_STORE = "gs://benchmark_spider_screenshots"
GCP_BUCKET_NAME = "benchmark_spider_screenshots"

GCS_PROJECT_ID = "uncork"

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
# AUTOTHROTTLE_ENABLED = True
# The initial download delay
# AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
# AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
# AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
