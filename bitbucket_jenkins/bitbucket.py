import logging
import requests


class BitBucketClient():
    BUILD_SUCCESSFUL = "SUCCESSFUL"
    BUILD_FAILED = "FAILED"
    BUILD_IN_PROGRESS = "INPROGRESS"

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def _do_req(self, method, url, data):
        logging.info("Sending %s request to bitbucket endpoint %s: %s" % (method, url, data))

        resp = requests.request(method, url, json=data, auth=(self.username,
                                                              self.password))

        logging.debug("Received %s response from bitbucket API: %s" % (resp.status_code,
                                                                       resp.content,))

    def url(self, owner, repo_slug, command_path):
        return ("https://api.bitbucket.org/2.0/repositories/{owner}/{repo_slug}"
               "{command_path}".format(owner=owner, repo_slug=repo_slug, command_path=command_path))

    def notify_build_changed(self, owner, repo_slug, revision, status, job_name, build_num=None, job_url=None):
        self._do_req("POST",
                     self.url(owner,
                              repo_slug,
                              "/commit/{revision}/statuses/build".format(revision=revision)),
                     {
                         "state": status,
                         "key": job_name,
                         "name": job_name,
                         "url": job_url,
                     })
