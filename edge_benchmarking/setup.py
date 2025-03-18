# Automatically created by: shub deploy

from setuptools import setup, find_packages

setup(
    name         = 'project',
    version      = '1.0',
    packages     = find_packages(),
    entry_points = {'scrapy': ['settings = edge_benchmarking.settings']},
    # package_data={
    #     'browserstack_benchmark': ['antibot_presets.json', 'antibot_signs.json', 'uncork-gcloud-auth.json', 'language_gen/*'],
    # }
)
