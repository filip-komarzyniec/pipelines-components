
## Testing framework overview

An architectural overview of how the testing of pipelines and their building components (should) work within this repository.

> [!WARNING]
> This is still a work in progress. The behaviour described in this document
> is in the PR and undergoes a review of the kubeflow-pipelines upstream community.

----

### Background -- problem statement

The pipelines-components repository consists of multiple separate and independent components building up different pipelines. The components might be reused between different pipelines or even different versions of the same pipeline.

The components and pipelines, being standard python programs, define their own sets of dependencies. In order to avoid any conflicts, the pipelines-components project-level metada files cannot define any dependencies apart from the `kfp` itself.

The components and pipelines, being standard python programs, need to be covered with unit/integration tests in order to become reliable and production-ready. The tests suite need all of the standard dependencies (and usually even more test-specific packages) during execution time in order to resemble the production environment as closely as possible. Mocking out the dependencies is obviously not an acceptable option.

Based on the above statements a clear problem arises --- how to ensure that each component or pipeline can be tested in an appropriate, isolated and always up-to-date environment, both locally and inside CI/CD pipelines?

### Background -- proposed solution

The most obvious response to the problem seems to be utilising the OCI images. Each compoent / pipeline ... TODOODODO

Clear benefits:

- native versioning and releasing of the components/pipelines separate from the whole kubeflow-pipelines project's release cycles,
- natural environment isolation
- enforcing industry best practises upon components/pipelines maintainers
- a container is the Kubeflow Pipelines' natural building block
- allows for easy sharing of components and whole pipelines

Minor inconveniences:

- small maintenance overhead for the authors
-

### Architecture & Flow

![Test execution flow](tests_execution_graph.svg)


### Best practises to write tests

### Caveats and assumptions

#### python environment is ready out of the box for commands executed in the container

No further steps (e.g. sourcing a venv) is needed to enable the target python env in the container process.

#### pytest and a few other necessary packages to be installed in the provided image will not ruin it

Current CI/CD pipeline sets up the python env first (`.github/actions/setup-python-ci/action.yml`) and proceeds to install `pipelines-components[test]`.
With the per component/pipeline image it's now obsolete, however the following packages are mandatory in order to run tests: `pytest pytest-cov pytest-timeout`.

#### All packages necessary to succesfully run tests are pre-installed on the provided image

#### internet access and public availability of the `tests.image` image

This should not be a big deal as the current CI/CD pipeline is connected to the internet as well.

#### `--verbose` flag does not affect container runs

The `--verbose` CLI flag is forwarded only to the host-local pytest invocation. Container
workers always use quiet mode regardless of the flag.

### Additional links

Slack discussion: https://redhat-internal.slack.com/archives/C09RJPFTNNT/p1779181078563379
Jira issue: https://redhat.atlassian.net/browse/RHOAIENG-67148
