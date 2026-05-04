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
  - [Pre-Commit Hooks](#pre-commit-hooks)
  - [Using the Admin UI](#using-the-admin-ui)
  - [Updating Packages](#updating-packages)
  - [Running Tests In Parallel](#running-tests-in-parallel)
  - [Visual Studio Code Integration](#visual-studio-code-integration)
    - [Debug from Visual Studio Code](#debug-from-visual-studio-code)
    - [Run Tests From Within Visual Studio Code](#run-tests-from-within-visual-studio-code)
- [Cognito](#cognito)
  - [Local Cognito](#local-cognito)
- [User management](#user-management)
- [OTEL](#otel)
  - [Environment Variables](#environment-variables)
  - [Adding a New Instrumentation](#adding-a-new-instrumentation)
  - [Log Correlation](#log-correlation)
  - [Sampling](#sampling)
  - [Local Telemetry](#local-telemetry)
- [Type Checking](#type-checking)
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

- python version 3.14
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- `docker` and `docker compose`

### Setup

To create and activate a virtual Python environment with all dependencies installed:

```bash
make setup
```

Then run the server

```bash
make serve
```

To seed local development test data (cognito users, organizations and user-role assignments):

```bash
make seed-local-testdata
```

To reset existing seeded users/organizations and re-apply the seed from scratch:

```bash
make reset-local-testdata
```

### Pre-Commit Hooks

This project uses pre-commit hooks to lint and type-check before committing. Pre-commits hooks can
either be bypassed entirely with the `--no-verify` option (`git commit --no-verify ...`), or
individually using the `SKIP` environment variable (`SKIP=lint git commit ...`).

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
uv sync --upgrade
```

To see what major/incompatible releases would be available, run:

```bash
uv pip list --outdated
```

To update packages to a new major release, run:

```bash
uv add logging-utilities~=5.0
```

### Running Tests In Parallel

Run tests with, for example, 16 workers:

```bash
pytest -n 16
```

### Visual Studio Code Integration

There are some possibilities to debug this codebase from within visual studio code.

#### Debug from Visual Studio Code

Start the server with `make serve-debug`. The bootup will wait with the execution until the debugger
is attached, which can most easily done by hitting F5.

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

To connect to a cognito instance running on AWS using your SSO User modify the client `__init__` to use the local session:

```python
# app/cognito/utils/client.py
class Client:
    """A low level client for managing cognito users and groups."""

    def __init__(self) -> None:
        from boto3 import Session
        session = Session(profile_name="<AWS_PROFILE_NAME>", region_name="<AWS_REGION_NAME>")
        self.user_pool_id = "<USER_POOL_ID>"
        self.client = session.client("cognito-idp")
```

## User management

The standard django `User` model (django.contrib.auth.models) is replaced by the
[CustomUser](./app/user/models.py) model. This model represents human as well as machine users.

Human users must exist in cognito and are created the first time they call service-control with a
valid AccessToken. The RemoteUserBackend (django.contrib.auth.backends) is extended by
[RemoteCustomUserBackend](./app/oauth2_proxy/middleware.py) to also save the cognito username. The
AccessToken uses the cognito user id (sub) as subject and is used as identifier in the
service-control model. Most cognito admin api calls (e.g. AdminUpdateUserAttributes) expect the
cognito username, which is why we also save it in the extended RemoteCustomUserBackend.

Machine users are always created via service-control api that generates a cognito app client. When
a machine user calls the api with an AccessToken, the user already exists and will not be created
by the RemoteCustomUserBackend.

The standard django `Groups` are not used, authorization is done externally via verified permissions.
The only exception is we still use the `is_superuser`/`is_staff` to allow the user to do everything
and log in to the admin UI. For humans these flags (both or none) are set if they are in the cognito
group `OAUTH2_PROXY_DJANGO_ADMIN_GROUPS`. For machine users the flags can be set (via admin ui).

## OTEL

[OpenTelemetry instrumentation](https://opentelemetry.io/docs/concepts/instrumentation/) can be done in many different ways, from fully automated zero-code instrumentation (otel-operator) to purely manual instrumentation.
We use the so called `OTEL programmatical instrumentation` approach where we import the specific instrumentation libraries and initialize them with the instrument() method of each library when serving requests with WSGI and when running management commands.

### Environment Variables

The following env variables can be used to configure OTEL

| Env Variable                                              | Default                    | Description                                                                                                                                          |
| --------------------------------------------------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| OTEL_SDK_DISABLED                                         | false                      | If set to "true", OTEL is disabled. See: https://opentelemetry.io/docs/specs/otel/configuration/sdk-environment-variables/#general-sdk-configuration |
| OTEL_ENABLE_BOTO                                          | false                      | If opentelemetry-instrumentation-botocore should be enabled or not.                                                                                  |
| OTEL_ENABLE_DJANGO                                        | false                      | If opentelemetry-instrumentation-django should be enabled or not.                                                                                    |
| OTEL_ENABLE_PSYCOPG                                       | false                      | If opentelemetry-instrumentation-psycopg should be enabled or not.                                                                                   |
| OTEL_ENABLE_LOGGING                                       | false                      | If opentelemetry-instrumentation-logging should be enabled or not.                                                                                   |
| OTEL_EXPERIMENTAL_RESOURCE_DETECTORS                      |                            | OTEL resource detectors, adding resource attributes to the OTEL output. e.g. `os,process`                                                            |
| OTEL_EXPORTER_OTLP_ENDPOINT                               | http://localhost:4317      | The OTEL Exporter endpoint, e.g. `opentelemetry-kube-stack-gateway-collector.opentelemetry-operator-system:4317`                                     |
| OTEL_EXPORTER_OTLP_HEADERS                                |                            | A list of key=value headers added in outgoing data. https://opentelemetry.io/docs/languages/sdk-configuration/otlp-exporter/#header-configuration    |
| OTEL_EXPORTER_OTLP_INSECURE                               | false                      | If exporter ssl certificates should be checked or not.                                                                                               |
| OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST  |                            | A comma separated list of request headers added in outgoing data. Regex supported. Use '.*' for all headers                                          |
| OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_RESPONSE |                            | A comma separated list of request headers added in outgoing data. Regex supported. Use '.*' for all headers                                          |
| OTEL_PYTHON_EXCLUDED_URLS                                 |                            | A comma separated list of url's to exclude, e.g. `checker`                                                                                           |
| OTEL_PYTHON_DJANGO_TRACED_REQUEST_ATTRS                   |                            | A comma separated list of attributes from the django request, e.g. `path_info,content_type`                                                          |
| OTEL_RESOURCE_ATTRIBUTES                                  |                            | A comma separated list of custom OTEL resource attributes, Must contain at least the service-name `service.name=service-shortlink`                   |
| OTEL_TRACES_SAMPLER                                       | parentbased_always_on      | Sampler to be used, see https://opentelemetry-python.readthedocs.io/en/latest/sdk/trace.sampling.html#module-opentelemetry.sdk.trace.sampling.       |
| OTEL_TRACES_SAMPLER_ARG                                   |                            | Optional additional arguments for sampler.                                                                                                           |

### Adding a New Instrumentation

1. Use `edot-bootstrap --action=requirements` to get a list of possible instrumentation libraries
2. Add all or the desired ones to the Pipfile.
3. Add the initialization to [otel.py](app/helpers/otel.py) together with a feature flag

Note: `edot-bootstrap` should be already installed via `infra-ansible-bgdi-dev`. If not, install it with `pipx install elastic-opentelemetry`.

### Log Correlation

The OpenTelemetry logging integration automatically injects tracing context into log statements. The following keys are injected into log record objects:

- otelSpanID
- otelTraceID
- otelTraceSampled

Note that although otelServiceName is injected, it will be empty. This is because the logging integration tries to read the service name from the trace provider, but our trace provider instance does not contain this resource attribute.

### Sampling

The python SDK supports ratio based [head sampling](https://opentelemetry.io/docs/concepts/sampling/#head-sampling). To enable, set

- OTEL_TRACES_SAMPLER=parentbased_traceidratio|traceidratio
- and OTEL_TRACES_SAMPLER_ARG=[0.0,1.0]

### Local Telemetry

Local telemetry can be tested by using one of the serve commands that use gunicorn, either 

```bash
make gunicornserve
```

or

```bash
make dockerrun
```

and visiting the Zipkin dashboard at [http://localhost:9411](http://localhost:9411).

## Type Checking

### Library Types

For type-checking, the external library [ty](https://docs.astral.sh/ty) is being used.

Some 3rd party libraries need to have explicit type stubs installed for the type checker
to work. Some of them can be found in [typeshed](https://github.com/python/typeshed). Sometimes dedicated
packages exist, as is the case with [django-stubs](https://pypi.org/project/django-stubs/).

If there aren't any type hints available, they can also be auto-generated with [stubgen](https://mypy.readthedocs.io/en/stable/stubgen.html)
