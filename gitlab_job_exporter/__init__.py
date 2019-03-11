import json
import time
import argparse
from urllib.request  import urlopen, Request
from urllib.error import URLError, HTTPError
from prometheus_client import Summary
from prometheus_client.core import GaugeMetricFamily
from dateutil.parser import parse

COLLECTION_TIME = Summary('gitlab_job_collector_collect_seconds',
                          'Time spent to collect metrics from Gitlab')

# metrics:
#
# gitlab_job_last_id{'GitRepo','Branch','Scope'}: number
# gitlab_job_last_created_timestamp{'GitRepo','Branch','Scope'}: unix timestamp
# gitlab_job_last_finished_timestamp{'GitRepo','Branch','Scope'}: unix timestamp
# gitlab_job_last_starting_duration_seconds{'GitRepo','Branch','Scope'}: seconds
# gitlab_job_last_running_duration_seconds{'GitRepo','Branch','Scope'}: seconds
# gitlab_job_last_total_duration_seconds{'GitRepo','Branch','Scope'}: seconds

def parse_args():
    parser = argparse.ArgumentParser(
        description='gitlab job exporter args using config file'
    )

    parser.add_argument(
        '-c', '--config',
        required=True,
        help='gitlab job exporter config file using json format',
    )

    return parser.parse_args()

def example_config():
    default_json_config = {"port":"9118", "interval":"10", "git_url":"https://<gitlab-example-url>", "git_project_id":"1234", "git_token":"XXXXXXXXXXXXXXXXXXXX", "git_branch":"gitlab_example_branch"}
    return default_json_config


def throw_exception(_exc, msg):

    raise RuntimeError(type(_exc), _exc, msg)


# Get json data from url
def _http_get_data(url, token):

    try:
        request = Request(url)
        request.add_header('PRIVATE-TOKEN', token)
        data_bin = urlopen(request)
        data_str = data_bin.read().decode('utf-8')
        data_json = json.loads(data_str)

    except (URLError, HTTPError) as exc:
        throw_exception(exc, 'Log: url={0}'.format(url))
    except TypeError as exc:
        throw_exception(exc, 'Log: url={0}'.format(url))
    except ValueError as exc:
        throw_exception(exc, 'Log: url={0}'.format(url))

    return data_json

class GitlabJobCollector():

    # Defaults
    default_timestamp = parse('1970/01/01 00:00:00.000+00:00')
    default_duration = default_timestamp - default_timestamp

    # Define status to monitor
    job_status = ["success", "failed", "canceled", "running", "skipped", "pending"]

    def __init__(self, git_url, git_project_id, git_token, git_branch):
        self._git_url = git_url
        self._git_project_id = git_project_id
        self._git_token = git_token
        self._git_branch = git_branch

        # Metrics to export
        self._prometheus_metrics = {}

        # Variable init
        self._git_repo_url = ''
        self._git_project_url = '{0}/api/v4/projects/{1}'.format(self._git_url, str(self._git_project_id))

    def collect(self):

        start = time.time()

        # Get url of git project
        project = _http_get_data(self._git_project_url, self._git_token)
        self._git_repo_url = project.get("http_url_to_repo")

        # Setup empty prometheus metrics
        self._setup_empty_prometheus_metrics()

        # Get all needed metrics
        for status in self.job_status:
            self._get_all_metrics(status)

        for metric in self._prometheus_metrics.values():
            yield metric

        # Scraping duration
        duration = time.time() - start
        COLLECTION_TIME.observe(duration)

    def _get_all_metrics(self, status):

        # Get last job
        # Git sorts jobs descending so we just have to select the first job of the first page...
        url = '{0}/jobs?scope={1}&per_page=1&page=1'.format(self._git_project_url, status)

        # Get all data of that job in json format
        job_data = _http_get_data(url, self._git_token)

        # Exract values needed to define metrics
        try:
            job        = job_data[0]
            job_id     = int(job['id'])
            created_at = parse(job['created_at'])
        except:
            job        = {}
            job_id     = -1
            created_at = self.default_timestamp

        try:
            started_at  = parse(job['started_at'])
        except:
            started_at  = self.default_timestamp

        try:
            finished_at = parse(job['finished_at'])
        except:
            finished_at = self.default_timestamp

        try:
            duration_total = float(job['duration'])
        except:
            duration_total = -1

        # Compute metric values of duration_starting, duration_running
        # starting
        if started_at == self.default_timestamp:
            duration_starting = self.default_duration
        else:
            duration_starting = started_at - created_at

        # running
        if finished_at == self.default_timestamp or started_at == self.default_timestamp:
            duration_running = self.default_duration
        else:
            duration_running = finished_at - started_at

        # Add data to metrics                            _
        self._prometheus_metrics['id'].add_metric([self._git_repo_url,
                                                   self._git_branch,
                                                   status],
                                                  job_id)
        self._prometheus_metrics['created_at'].add_metric([self._git_repo_url,
                                                           self._git_branch,
                                                           status],
                                                          created_at.timestamp())
        self._prometheus_metrics['finished_at'].add_metric([self._git_repo_url,
                                                            self._git_branch,
                                                            status],
                                                           finished_at.timestamp())
        self._prometheus_metrics['duration_starting'].add_metric([self._git_repo_url,
                                                                  self._git_branch,
                                                                  status],
                                                                 duration_starting.total_seconds())
        self._prometheus_metrics['duration_running'].add_metric([self._git_repo_url,
                                                                 self._git_branch,
                                                                 status],
                                                                duration_running.total_seconds())
        self._prometheus_metrics['duration_total'].add_metric([self._git_repo_url,
                                                               self._git_branch,
                                                               status],
                                                              duration_total)

    def _setup_empty_prometheus_metrics(self):

        # Define metrics to export
        self._prometheus_metrics = {

            'id':
                GaugeMetricFamily('gitlab_job_last_id',
                                  'Gitlab job ID of the last job',
                                  labels=['GitRepo', 'Branch', 'Scope']),
            'created_at':
                GaugeMetricFamily('gitlab_job_last_created_timestamp',
                                  'Gitlab job creation timestamp of the last job',
                                  labels=['GitRepo', 'Branch', 'Scope']),
            'finished_at':
                GaugeMetricFamily('gitlab_job_last_finished_timestamp',
                                  'Gitlab job finished timestamp of the last job',
                                  labels=['GitRepo', 'Branch', 'Scope']),
            'duration_starting':
                GaugeMetricFamily('gitlab_job_last_starting_duration_seconds',
                                  'Gitlab job time between creation and running of the last job (-1: No duration available)',
                                  labels=['GitRepo', 'Branch', 'Scope']),
            'duration_running':
                GaugeMetricFamily('gitlab_job_last_running_duration_seconds',
                                  'Gitlab job time between creation and finishing of the last job (-1: No duration available)',
                                  labels=['GitRepo', 'Branch', 'Scope']),
            'duration_total':
                GaugeMetricFamily('gitlab_job_last_total_duration_seconds',
                                  'Gitlab job time between creation and finishing of the last job (-1: No duration available)',
                                  labels=['GitRepo', 'Branch', 'Scope'])
        }
