# GitLab Students' Monitor

[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](http://www.gnu.org/licenses/gpl-3.0)

This is a simple [Flask Admin](https://flask-admin.readthedocs.io/) application
that allows teachers using [RepoBee](https://repobee.org/) to monitor students'
progress on [GitLab](https://about.gitlab.com/) via
[python-gitlab](https://python-gitlab.readthedocs.io/).

## Example configuration file

```toml
[environment]
SQLITE_DATABASE_FILE=<path to sqlite database file>
LOG_LEVEL="INFO"
[flask]
SECRET_KEY=<secret key>
FLASK_ADMIN_SWATCH="lumen"
FLASK_ADMIN_FLUID_LAYOUT="true"
[gitlab]
ENDPOINT=<the gitlab instance endpoint>
TOKEN=<a gitlab private token>
GROUP=<the repobee group id>
BASEURL=<the repobee group base URL>
```

## Running with Docker

First build the image with `./bin/build <VERSION>`, then run it with `./bin/run
<VERSION>`; the image will run using the file `conf.toml` in the current
directory as a configuration file (see above) and saving the database in the
current directory as `gsm.db` (the configuration is overridden by the
`GSM_SQLITE_DATABASE_FILE` environment variable defined in the `Dockerfile`).