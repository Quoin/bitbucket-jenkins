# Bitbucket Jenkins Integrator

This is a simple Python Bottle web app that facilitates automatically building
Bitbucket Pull Requests in Jenkins.  This acts as a middleman between Jenkins
and Bitbucket.  Unfortunately the existing Jenkins plugin for building pull
requests from Bitbucket has some major shortcomings, and thus this solution was
born.  The app offers two endpoints: `/bitbucket-pr-webhook/` and
`/jenkins-notifier/`, which serve the Bitbucket Pull Request webhook and the
Jenkins build notification handler, respectively.

When properly configured, any new or modified Pull Requests made in a Bitbucket
repository will be automatically tested in Jenkins.  The various jobs
will show up as Bitbucket "builds" and will link to the repsective Jenkin's
build page.

## Configuring Bitbucket
You should setup a webhook that handles the "Pull Request: Created" and "Pull
Request: Updated" triggers.  Set the URL for the hook to `http://<integrator
app host>/bitbucket-pr-webhook/?jobs=<jobs to run>`, where `<integrator app
host>` is the hostname of this application deployed somewhere, and `<jobs to
run>` is a comma separated list of jobs that you want triggered for each pull
request.

## Configuring Jenkins
Install the [Notification
Plugin](https://wiki.jenkins-ci.org/display/JENKINS/Notification+Plugin) in
order for Jenkins to work its magic.  Currently version 1.10 is tested and
supported, but other versions might work as well.  The configuration for the
plugin will be setup automatically in each job by this app before it is needed.

Also, all Jenkins jobs must have a string build parameter called `revision`
that is set as the "Branches to build -> Branch Specifier" option.  This
parameter will be set by this app based on the commit hash of the PR.

This app supports HTTP Basic auth when communicating with Jenkins.  It also
supports connecting without authentication, although this is not recommended.

##Envvars

The following envvars should be set in the container running this server:

 - `BITBUCKET_USERNAME`: The username of the bitbucket bot user
 - `BITBUCKET_PASSWORD`: The password of that user
 - `JENKINS_URL`: The base URL of the Jenkins server (e.g. `https://my.jenkins.com`)
 - `JENKINS_USERNAME`: The username to access the Jenkins instance (i.e. through HTTP Basic auth).
 - `JENKINS_PASSWORD`: The password for that user
