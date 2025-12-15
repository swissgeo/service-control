# service-control

| Branch | Status |
|--------|-----------|
| develop | ![Build Status](https://codebuild.eu-central-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoia2xnRW0xR0wwSm10aFp4UTJJRmRKUEl0blFzZ0RQelFXczFZRnQzVlVrcTBMSUFMdjIxYnZqZXdlQjlqMXBXSlV2V3dPSEFjclEydDZ2QVFsTU5hTDhFPSIsIml2UGFyYW1ldGVyU3BlYyI6IlpxZ2l4b0tncFJqVHpwRnIiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=develop) |
| main | ![Build Status](https://codebuild.eu-central-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoia2xnRW0xR0wwSm10aFp4UTJJRmRKUEl0blFzZ0RQelFXczFZRnQzVlVrcTBMSUFMdjIxYnZqZXdlQjlqMXBXSlV2V3dPSEFjclEydDZ2QVFsTU5hTDhFPSIsIml2UGFyYW1ldGVyU3BlYyI6IlpxZ2l4b0tncFJqVHpwRnIiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=main) |

## Table of Content

- [Table of Content](#table-of-content)
- [Summary Of The Project](#summary-of-the-project)
- [Logging Standard Django Management Commands](#logging-standard-django-management-commands)
- [Local Development](#local-development)
  - [Dependencies](#dependencies)
  - [Setup](#setup)
  - [Using the Admin UI](#using-the-admin-ui)
  - [Updating Packages](#updating-packages)
  - [Running Tests In Parallel](#running-tests-in-parallel)
  - [Visual Studio Code Integration](#visual-studio-code-integration)
    - [Debug from Visual Studio Code](#debug-from-visual-studio-code)
    - [Run Tests From Within Visual Studio Code](#run-tests-from-within-visual-studio-code)
- [Cognito](#cognito)
  - [Local Cognito](#local-cognito)
- [Type Checking](#type-checking)
  - [Mypy](#mypy)
  - [Library Types](#library-types)

## Summary Of The Project

`service-control` provides and manages the verified permissions.  TBC

## Logging Standard Django Management Commands

This project uses a modified `manage.py` that supports redirecting the output of the standard
Django management commands to the logger. For this, simply add `--redirect-std-to-logger`, e.g.:

```bash
app/manage.py migrate --redirect-std-to-logger
```

## Local Development

### Dependencies

Prerequisites on host for development and build:

- python version 3.13
- [pipenv](https://pipenv-fork.readthedocs.io/en/latest/install.html)
- `docker` and `docker compose`

### Setup

To create and activate a virtual Python environment with all dependencies installed:

```bash
make setup
```

To start the local postgres container, run this:

```bash
make start-local-db
```

To initialize the database, run this (at least once):

```bash
app/manage.py init_db && app/manage.py migrate
```

Once your database has been initialized, you can later sync it with the latest Django migrations by running only:

```bash
app/manage.py migrate
```

### Using the Admin UI

`service-control` authenticates using an OAuth2 proxy which simply sets some headers. To locally use
the admin UI during development, make sure to pass these headers, for example with a browser plugin
such as https://mybrowseraddon.com/modify-header-value.html:

- `X-Auth-Request-User`: any user name or ID
- `X-Auth-Request-Preferred-Username`: any user name
- `X-Auth-Request-Email`: any e-mail address
- `X-Auth-Request-Groups`: the value of OAUTH2_PROXY_DJANGO_ADMIN_GROUPS

### Updating Packages

All packages used in production are pinned to a major version. Automatically updating these packages
will use the latest minor (or patch) version available. Packages used for development, on the other
hand, are not pinned unless they need to be used with a specific version of a production package
(for example, boto3-stubs for boto3).

To update the packages to the latest minor/compatible versions, run:

```bash
pipenv update --dev
```

To see what major/incompatible releases would be available, run:

```bash
pipenv update --dev --outdated
```

To update packages to a new major release, run:

```bash
pipenv install logging-utilities~=5.0
```

### Running Tests In Parallel

Run tests with, for example, 16 workers:

```bash
pytest -n 16
```

### Visual Studio Code Integration

There are some possibilities to debug this codebase from within visual studio code.

#### Debug from Visual Studio Code

In order to debug the service from within vs code, you need to create a launch-configuration. Create
a folder `.vscode` in the root folder if it doesn't exist and put a file `launch.json` with this content
in it:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python Debugger: Attach",
      "type": "debugpy",
      "request": "attach",
      "justMyCode": false,
      "connect": {
        "host": "localhost",
        "port": 5678
      }
    }
  ]
}
```

Alternatively, create the file via menu "Run" > "Add Configuration" by choosing

- Debugger: Python Debugger
- Debug Configration: Remote Attach
- Hostname: `localhost`
- Port number: `5678`

Now you can start the server with `make serve-debug`.
The bootup will wait with the execution until the debugger is attached, which can most easily done by hitting F5.

#### Run Tests From Within Visual Studio Code

The unit tests can also be invoked inside vs code directly (beaker icon).
To do this you need to have the following settings either in
`.vscode/settings.json` or in your workspace settings:

```json
  "python.testing.pytestArgs": [
    "app"
  ],
  "python.testing.unittestEnabled": false,
  "python.testing.pytestEnabled": true,
```

You can also create this file interactively via menu "Python: Configure Tests"
in the Command Palette (Ctrl+Shift+P).

For the automatic test discovery to work, make sure that vs code has the Python
interpreter of your venv selected (`.venv/bin/python`).
You can change the Python interpreter via menu "Python: Select Interpreter"
in the Command Palette.

## Cognito

This project uses Amazon Cognito user identity and access management.

### Local Cognito

For local testing the connection to cognito, [cognito-local](https://github.com/jagregory/cognito-local) is used.
`cognito-local` stores all of its data as simple JSON files in its volume (`.volumes/cognito/db/`).

You can also use the AWS CLI together with `cognito-local` by specifying the local endpoint, for example:

```bash
aws --endpoint $COGNITO_ENDPOINT_URL cognito-idp list-users --user-pool-id $COGNITO_POOL_ID
```

## Type Checking

### Mypy

Type checking can be done by either calling `mypy` or the make target: 

```sh
make type-check
```

This will check all files in the repository.

### Library Types

For type-checking, the external library [mypy](https://mypy.readthedocs.io) is being used. See the [type hints cheat sheet](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html) for help on getting the types right.

Some 3rd party libraries need to have explicit type stubs installed for the type checker
to work. Some of them can be found in [typeshed](https://github.com/python/typeshed). Sometimes dedicated
packages exist, as is the case with [django-stubs](https://pypi.org/project/django-stubs/).

If there aren't any type hints available, they can also be auto-generated with [stubgen](https://mypy.readthedocs.io/en/stable/stubgen.html)

SOME CHANGE TO BE REMOVED. Second change
