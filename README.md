# Testoria

API testing for any project, on any platform. Testoria lets you write API tests as YAML or JSON and run them against any HTTP API, whatever language the API is written in. It also includes:

- a mock server that reads WireMock and MockServer files
- a sample REST API to practise against
- quick load testing and basic security checks
- generators that turn OpenAPI/Swagger files and Postman collections into tests

The original Python, JavaScript and Java example suites are still here, and they all run against the sample API out of the box.

## Install (one command)

```bash
curl -fsSL https://raw.githubusercontent.com/Testoria-Framework/testoria/main/install.sh | bash
```

Pass options after `bash -s --`:

```bash
curl -fsSL https://raw.githubusercontent.com/Testoria-Framework/testoria/main/install.sh | bash -s -- --all --verify
```

From a checkout, run `./install.sh [options]`.

| Option | What it does |
| --- | --- |
| *(none)* | Installs the `testoria` CLI into an isolated virtualenv and puts a launcher on your PATH |
| `--js` | Installs the Node.js packages for the JavaScript suites |
| `--java` | Downloads the Maven dependencies for the Java suites with `./mvnw` |
| `--perf` | Installs locust, and k6 too when combined with `--system-deps` |
| `--docker` | Builds the `testoria:latest` image |
| `--all` | All of the above |
| `--system-deps` | Installs missing Python, Node, JDK or git with brew, apt, dnf, yum, pacman, apk, zypper, winget or choco |
| `--init DIR` | Creates a starter project in `DIR` |
| `--verify` | Runs every installed suite against the sample API |
| `--dir DIR` / `--bin-dir DIR` | Where to put the checkout and the launcher (defaults: `~/.testoria`, `~/.local/bin`) |
| `--branch NAME` / `--python PATH` | Git branch to install, Python interpreter to use |
| `--no-path`, `-y`, `-q` | Don't edit shell profiles, don't ask before package installs, less output |
| `--uninstall` | Removes the virtualenv and the launcher |

The installer works on macOS, Linux, WSL and Windows (Git Bash or MSYS2). On Windows it also creates a `testoria.cmd` launcher. The CLI only needs Python 3.8+ and PyYAML.

You can also install it with `pip install .` or run it with Docker: `docker run --rm -v "$PWD:/work" testoria run`.

## Quick start

```bash
testoria init my-api-tests && cd my-api-tests
testoria run --mock            # runs the example spec against the built-in mock server
testoria run -e staging        # same tests against a real environment from testoria.yaml
```

## Writing tests

```yaml
name: Users API
base_url: "{{ env.API_URL | default('http://localhost:8080') }}"
headers:
  Authorization: "Bearer {{ token }}"

setup:
  - request: {method: POST, url: /auth/login, json: {username: me, password: "{{ env.PASSWORD }}"}}
    extract: {token: $.token}

tests:
  - name: create user
    tags: [smoke]
    request:
      method: POST
      url: /users
      json: {name: "{{ $randomName }}", email: "{{ $randomEmail }}"}
    expect:
      status: 201                 # also: "2xx", [200, 204], "200-299"
      max_time_ms: 1000
      headers: {Content-Type: json}
      json:
        $.id: {exists: true, type: integer}
        $.email: {matches: "@example.com$"}
      schema: {type: object, required: [id, name, email]}
    extract: {user_id: $.id}

  - name: invalid input - {{ case }}
    data:                         # data-driven; can also be a CSV, YAML or JSON file path
      - {case: no email, body: {name: Ada}}
      - {case: bad email, body: {name: Ada, email: nope}}
    request: {method: POST, url: /users, json: "{{ body }}"}
    expect: {status: 400}

  - name: fetch it
    retries: 3                    # retry flaky checks
    request: {method: GET, url: "/users/{{ user_id }}"}
    expect: {json: {$.id: "{{ user_id }}"}}
```

- **Operators:** `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `between`, `approx`, `contains`, `not_contains`, `matches`, `type`, `exists`, `length`, `min_length`, `max_length`, `in`, `not_in`, `starts_with`, `ends_with`, `empty`, `not_empty`, `is_null`, `schema`.
- **JSON paths:** `$.a.b`, `$.list[0]`, `$.list[-1]`, `$.list[*].id`, `$..id`, `$.list.length()`.
- **Templates:** use `{{ var }}`, `{{ env.NAME }}` and `{{ response.body.x }}`, plus the filters `default`, `upper`, `lower`, `int`, `float`, `str`, `length`, `json`, `b64encode` and `b64decode`. Built-in values: `$uuid`, `$timestamp`, `$isoNow`, `$randomInt(1,10)`, `$randomString(8)`, `$randomEmail`, `$randomName`.
- **Extract:** from a JSON path, `header: X-Request-Id`, `regex: "id=(\\d+)"` or `status`.
- **Auth:** `auth: {type: bearer, token: ...}`, `{type: basic, username, password}` or `{type: apikey, header, key}`. Sensitive headers are masked in reports.

### Project config (`testoria.yaml`)

```yaml
tests: [tests/api]
reports: [html, junit, json]
default_env: local
environments:
  local:   {base_url: "http://127.0.0.1:8080"}
  staging: {base_url: https://staging.example.com, headers: {Authorization: "Bearer {{ env.STAGING_TOKEN }}"}}
mock: {port: 8080, mappings: [mocks], db: mocks/db.json, auto_start: false}
```

Testoria also loads a `.env` file from the project folder.

## Commands

| Command | Purpose |
| --- | --- |
| `testoria run [paths]` | Run specs. Options: `-e env`, `-u url`, `-t/-x tag`, `-k regex`, `--var k=v`, `-w N` (parallel), `--retries`, `--fail-fast`, `--dry-run`, `--mock`, `--open`, `--report html,junit,json` |
| `testoria watch` | Re-run whenever a spec changes |
| `testoria mock [dirs] [--db db.json]` | Mock server. Reads WireMock and MockServer files, supports WireMock-style response templating, delays and faults, and turns every top-level key in `--db` into a CRUD resource. Admin endpoints are under `/__admin` |
| `testoria demo-api` | Sample API with users, products, orders, login, a rate limit, validation and auth |
| `testoria load URL -u 20 -d 30 --p95 500` | Load test that reports p50/p90/p95/p99 latency, throughput (RPS) and error rate, and fails when a threshold is missed |
| `testoria scan URL [--active] [--check-auth]` | Basic security checks: TLS, security headers, CORS, cookies, version leaks, TRACE, auth bypass and simple injection probes. **Only scan systems you own or are allowed to test.** |
| `testoria import openapi spec.yaml -o tests/api/generated.yaml` | Generate smoke and contract tests from OpenAPI 3 or Swagger 2. `--include-mutations` adds POST/PUT/DELETE tests |
| `testoria import postman collection.json -o tests/api/pm.yaml` | Convert a Postman v2 collection |
| `testoria init`, `testoria doctor` | Create a starter project, check which tools are installed |

Reports go to `reports/`. The `report.html` file needs no internet connection and lets you filter and search tests. `junit.xml` works with any CI server, and `results.json` is for your own scripts.

## Bundled language suites

```bash
scripts/run_tests.sh --language python,javascript,java --type all     # against the sample API
scripts/run_tests.sh --language python --type security --base-url https://api.mycompany.com
scripts/run_tests.sh --type performance                               # testoria load, plus k6 if installed
```

- **Python** (`pytest`, `requests`, `assertpy`): `core/clients/base_api_client.py`, `core/assertions/python_assertions.py`
- **JavaScript** (`mocha`, `axios`, `chai`): `core/clients/base_api_client.js`, `core/assertions/js_assertions.js`
- **Java** (`JUnit 5`, `REST Assured`): `src/main/java/core/...`, run with `./mvnw test`

All three read `API_BASE_URL`. When it isn't set, they start the sample API on a free port. Allure results are written to `reports/allure-results/<language>`, and `--report` builds the Allure HTML report when the `allure` CLI is installed. Older load-test scripts for k6, Locust and JMeter are in `tests/performance_tests`.

## CI/CD

Ready-made pipelines: `.github/workflows/main.yml` (Linux, macOS and Windows, with Python, JavaScript, Java and Docker jobs), `.gitlab-ci.yml` and `Jenkinsfile`. Copies are also in `ci_cd/`. Each pipeline installs with `./install.sh` and publishes JUnit results.

## Development

```bash
./install.sh --all
.venv/bin/python -m pytest tests/unit          # framework unit tests
scripts/run_tests.sh --language all --type all # everything
```

## License

MIT
