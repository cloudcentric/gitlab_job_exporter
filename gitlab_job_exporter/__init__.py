#!/usr/bin/env python3
import json
import time
from dateutil.parser import parse
try:
    from urllib.request  import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request
from prometheus_client import Summary
from prometheus_client.core import GaugeMetricFamily

COLLECTION_TIME = Summary('gitlab_job_collector_collect_seconds', 'Time spent to collect metrics from Gitlab')  

# metrics:
#
# gitlab_job_id_last_{status}['GitRepo','Branch']: number
# gitlab_job_created_timestamp_last_{status}['GitRepo','Branch']: unix timestamp
# gitlab_job_duration_starting_seconds_last_{status}['GitRepo','Branch']: seconds
# gitlab_job_duration_running_seconds_last_{status}['GitRepo','Branch']: seconds
# gitlab_job_duration_seconds_last_{status}['GitRepo','Branch']: seconds 

# Download data via http get
def _http_get_data(url,token):
    request = Request(url)
    request.add_header('PRIVATE-TOKEN', token)
    data = json.load(urlopen(request))
    return data

# Get url of gitlab repo
def _get_repo_url(git_url,project_id,token):
    git_project_url = git_url + str(project_id)
    project = _http_get_data(git_project_url, token)
    return project.get("http_url_to_repo")


class GitlabJobCollector():

    # Currently only success and failed seems to be interesting
    #job_status = [ "success", "pending", "running", "failed", "canceled", "skipped", "undefined" ]
    job_status = [ "success", "failed" ]

    def __init__(self, git_url, git_project_id, git_token, git_branch):
        self._git_url = git_url
        self._git_project_id = git_project_id
        self._git_token = git_token
        self._git_branch = git_branch


    def collect(self):

        start = time.time()  
        
        # Get url of git project
        self.git_repo_url = _get_repo_url(self._git_url, self._git_project_id, self._git_token)

        # Setup empty prometheus metrics
        self._setup_empty_prometheus_metrics()

        # Get all needed metrics
        for status in self.job_status:
           self._get_all_metrics(status)

        for status in self.job_status:
            for metric in self._prometheus_metrics[status].values():
                yield metric

        # Scraping duration
        duration = time.time() - start
        COLLECTION_TIME.observe(duration)

    def _get_all_metrics(self,status):

        job_data = {}

        # Get last job of desired status. 
        # Git sorts jobs descending so we just have to select the first job of the first page...
        url = self._git_url + self._git_project_id + '/jobs?scope={0}&per_page=1&page=1'.format(status)

        job_data[status] = _http_get_data(url,self._git_token)

        # Get values needed to define metrics
        for job in job_data[status]:
            job_id          = job.get("id")
            job_created_at  = parse(job.get("created_at"))
            job_started_at  = parse(job.get("started_at"))
            job_finished_at = parse(job.get("finished_at"))
            job_duration_starting = job_started_at - job_created_at
            job_duration_running  = job_finished_at - job_started_at
            job_duration_total    = job.get("duration")

        # Add data to metrics
        self._prometheus_metrics[status]['job_id'].add_metric([self.git_repo_url,self._git_branch], job_id)
        self._prometheus_metrics[status]['job_created_at'].add_metric([self.git_repo_url,self._git_branch], job_created_at.timestamp())
        self._prometheus_metrics[status]['job_duration_starting'].add_metric([self.git_repo_url,self._git_branch], job_duration_starting.total_seconds())
        self._prometheus_metrics[status]['job_duration_running'].add_metric([self.git_repo_url,self._git_branch], job_duration_running.total_seconds())
        self._prometheus_metrics[status]['job_duration_total'].add_metric([self.git_repo_url,self._git_branch], job_duration_total)

    def _setup_empty_prometheus_metrics(self):

        # Metrics to export
        self._prometheus_metrics = {}

        for status in self.job_status:
            self._prometheus_metrics[status] = {

              'job_id': 
                  GaugeMetricFamily('gitlab_job_id_last_{0}'.format(status),
                                    'Gitlab job ID of the last {0} job'.format(status),
                                    labels = ['GitRepo','Branch']),
              'job_created_at': 
                  GaugeMetricFamily('gitlab_job_created_timestamp_last_{0}'.format(status),
                                    'Gitlab job creation timestamp of the last {0} job'.format(status),
                                    labels = ['GitRepo','Branch']),
              'job_duration_starting': 
                  GaugeMetricFamily('gitlab_job_duration_starting_seconds_last_{0}'.format(status),
                                    'Gitlab job time between creation and running of the last {0} job'.format(status),
                                    labels = ['GitRepo','Branch']),
              'job_duration_running': 
                  GaugeMetricFamily('gitlab_job_duration_running_seconds_last_{0}'.format(status),
                                    'Gitlab job time between creation and finishing of the last {0} job'.format(status),
                                    labels = ['GitRepo','Branch']),
              'job_duration_total': 
                  GaugeMetricFamily('gitlab_job_duration_seconds_last_{0}'.format(status),
                                    'Gitlab job time between creation and finishing of the last {0} job'.format(status),
                                    labels = ['GitRepo','Branch'])
            }

