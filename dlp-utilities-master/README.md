# DLP Utilities for Dataiku Project Pipelines

## Documentation

Template CI/CD pipelines for Dataiku projects. Can only be used on Dataiku projects.

## How to Use?

### Import CI/CD (non-prod + R&D):

1. Create a `.gitlab-ci.yml` file inside your project repository.
2. Add the following lines:
    ```yaml
    include:
      # pipeline steps
      - project: 'dm/bpls/dlp/dlp_evolution/dlp-utilities'
        ref: master
        file: 'pipeline/pipeline.gitlab-ci.yml'
    ```
3. Add the Sonar configuration file: `sonar-project.properties`
    ```properties
    sonar.projectKey=<ENTER SONAR PROJECT KEY HERE>
    sonar.sourceEncoding=UTF-8
    sonar.qualitygate.wait=true
    sonar.scm.provider=git
    sonar.sources=gitlab-ci
    sonar.test.inclusions=datasets,explore,gitlab-ci,ipython_notebooks,pip,recipes,zones,venv
    sonar.exclusions=lib/python,target/*
    sonar.tests=lib/python
    sonar.python.version=3.9
    sonar.python.xunit.reportPath=target/xunit-result-app.xml
    sonar.python.coverage.reportPaths=target/coverage.xml
    ```
4. Ensure you have the Dataiku `params.json` file.

## Pipeline Explanation

### CI/CD (non-prod + R&D):

1. **Stage pre-config**: Clone the dlp-utilities public repo and get the API key from HVault. Add these dependencies to the artifacts.
2. **Stage test**: Initialize the test Python environment. Run pytest located in `lib/python`.
3. **Stage sonar scan**: Scan the project according to the Sonar configuration.
4. **Stage bundle**: Run the package/publish script from the dlp-utilities repo.
5. **Stage deploy**: Run the deploy script from the dlp-utilities repo.

## Content

### pip

- `pip/pip.conf`: Contains pip configuration for Artifactory.

### requirements(-test).txt

- `requirements.txt`: Contains a list of Python packages for dlp-utilities Python scripts.
- `requirements-test.txt`: Contains a list of Python packages for Dataiku unit tests.

## Python Scripts

- `run_package_and_publish_use_case_indus.py` & `run_deploy_use_case_indus.py`: Python scripts that use the Dataiku API to run Dataiku Macros with the correct parameters. These scripts get some parameters from the `params.json` file located inside the project repositories.