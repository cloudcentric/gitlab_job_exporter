# Gitlab Job Exporter

Prometheus exporter providing some metrics concerning gitlab job runtime

## Installation

```
pip install gitlab_job_exporter
```
In the example folder exists a sample systemd unit file template.

## Usage

Configuration file

`/etc/prometheus/gitlab_job_exporter.json`

The exporter needs a configuration file in json format. The location of that file has to be passed via command line argument:

`./gitlab_job_exporter --config /etc/prometheus/gitlab_job_exporter.json`

Example configuration file:

```json
{
  "port":"9118",
  "interval":"10",
  "git_url":"<gitlab-url>",
  "git_project_id":"1234",
  "git_token":"XXXXXYYYYYYZZZZZZ",
  "git_branch":"gitlab_branch_example"
}
```
