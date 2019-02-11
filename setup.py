#!/usr/bin/env python
from setuptools import setup, find_packages

def readme():
    with open('README.md') as f:
        return f.read()

setup(
    name="gitlab-job-exporter",
    version="0.0.7",
    author="Sven Hertzberg",
    author_email="sven.hertzberg@codecentric.cloud",
    description="Package to scrape running_time, duration_time, status, etc. of Gitlab jobs using prometheus time series format",
    license='MIT',
    long_description=readme(),
    url="https://gitlab.codecentric.de/cloudcentric/openstack-gitlab-runner",
    include_package_data = True,
    scripts=['bin/gitlab_job_exporter'],
    packages=find_packages(),
    install_requires=[
        'prometheus-client',
        'python-dateutil',
        'urllib3',
        'requests'
    ],
    zip_safe=False
)
