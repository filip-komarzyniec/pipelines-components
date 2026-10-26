
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

<svg viewBox="0 0 620 1200" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    xmlns="http://www.w3.org/2000/svg" style="max-width:640px;width:100%;height:auto;display:block;overflow:visible">
    <defs>
        <marker id="a" markerWidth="10" markerHeight="7" refX="8" refY="3.5" orient="auto"
            markerUnits="userSpaceOnUse">
            <polyline points="0,1 8,3.5 0,6" fill="none" stroke="#b0afa9" stroke-width="1.5"
                stroke-linejoin="round" />
        </marker>
        <marker id="ag" markerWidth="10" markerHeight="7" refX="8" refY="3.5" orient="auto"
            markerUnits="userSpaceOnUse">
            <polyline points="0,1 8,3.5 0,6" fill="none" stroke="#059669" stroke-width="1.5"
                stroke-linejoin="round" />
        </marker>
        <filter id="fs" x="-30%" y="-30%" width="160%" height="160%">
            <feDropShadow dx="0" dy="1" stdDeviation="3" flood-color="#000" flood-opacity="0.05" />
        </filter>
        <filter id="fm" x="-30%" y="-30%" width="160%" height="160%">
            <feDropShadow dx="0" dy="2" stdDeviation="6" flood-color="#000" flood-opacity="0.10" />
        </filter>
    </defs>

    <!-- START -->
    <rect x="185" y="20" width="250" height="52" rx="26" fill="#6d28d9" filter="url(#fm)" />
    <text x="310" y="46" dy="0.35em" text-anchor="middle" fill="white" font-size="15" font-weight="600"
        letter-spacing="-0.01em">Start Tests</text>

    <line x1="310" y1="72" x2="310" y2="100" stroke="#b0afa9" stroke-width="1.5" marker-end="url(#a)" />

    <!-- DISCOVER TEST DIRECTORIES -->
    <rect x="72" y="104" width="476" height="88" rx="10" fill="white" stroke="#2563eb"
        stroke-width="1.5" filter="url(#fs)" />
    <text x="310" y="130" text-anchor="middle" fill="#111110" font-size="14" font-weight="600">Discover Test Directories</text>
    <text x="310" y="152" text-anchor="middle" fill="#6b6a65" font-size="12">From component/pipeline paths</text>
    <text x="310" y="170" text-anchor="middle" fill="#6b6a65" font-size="12">Find all tests/ directories</text>

    <line x1="310" y1="192" x2="310" y2="218" stroke="#b0afa9" stroke-width="1.5" marker-end="url(#a)" />

    <!-- FOR EACH LOOP -->
    <rect x="54" y="222" width="512" height="102" rx="10" fill="white" stroke="#2563eb"
        stroke-width="1.5" stroke-dasharray="8,4" filter="url(#fs)" />
    <rect x="54" y="222" width="112" height="22" rx="6" fill="#2563eb" opacity="0.12" />
    <text x="110" y="233" dy="0.35em" text-anchor="middle" fill="#2563eb" font-size="10" font-weight="700"
        letter-spacing="0.06em">FOR EACH</text>
    <text x="310" y="276" text-anchor="middle" fill="#111110" font-size="14" font-weight="600">Test Directory</text>
    <text x="310" y="298" text-anchor="middle" fill="#6b6a65" font-size="12">Parse metadata.yaml · Group by tests.image presence</text>

    <line x1="310" y1="324" x2="310" y2="350" stroke="#b0afa9" stroke-width="1.5" marker-end="url(#a)" />

    <!-- DECISION DIAMOND -->
    <path d="M310,354 L428,432 L310,510 L192,432 Z" fill="#fffbeb" stroke="#d97706" stroke-width="2"
        filter="url(#fs)" />
    <text x="310" y="423" dy="0.35em" text-anchor="middle" fill="#111110" font-size="13" font-weight="600">Container</text>
    <text x="310" y="443" dy="0.35em" text-anchor="middle" fill="#111110" font-size="13" font-weight="600">tests?</text>

    <!-- YES: down -->
    <text x="320" y="519" fill="#059669" font-size="11" font-weight="700" letter-spacing="0.06em">YES</text>
    <line x1="310" y1="510" x2="310" y2="538" stroke="#059669" stroke-width="2" marker-end="url(#ag)" />

    <!-- NO: left → down → right, rejoins at convergence dot -->
    <text x="187" y="423" dy="0.35em" text-anchor="end" fill="#6b6a65" font-size="11" font-weight="700"
        letter-spacing="0.06em">NO</text>
    <polyline points="192,432 44,432 44,861 300,861" fill="none" stroke="#b0afa9" stroke-width="1.5"
        stroke-dasharray="5,3" marker-end="url(#a)" />

    <!-- PULL CONTAINER IMAGES -->
    <g opacity="0.4">
        <rect x="95" y="547" width="440" height="96" rx="10" fill="white" stroke="#059669" stroke-width="1.5" />
    </g>
    <rect x="90" y="542" width="440" height="96" rx="10" fill="white" stroke="#059669"
        stroke-width="1.5" filter="url(#fs)" />
    <text x="310" y="566" text-anchor="middle" fill="#111110" font-size="14" font-weight="600">Pull Container Images</text>
    <text x="310" y="586" text-anchor="middle" fill="#6b6a65" font-size="12">Retry ~30min (6min intervals) if image doesn't exist</text>
    <text x="310" y="614" text-anchor="middle" fill="#059669" font-size="11" font-weight="600">⚡ up to 2 in parallel</text>

    <line x1="310" y1="638" x2="310" y2="660" stroke="#b0afa9" stroke-width="1.5" marker-end="url(#a)" />

    <!-- RUN TESTS IN CONTAINERS -->
    <g opacity="0.25">
        <rect x="100" y="674" width="440" height="104" rx="10" fill="#ecfdf5" stroke="#059669" stroke-width="1.5" />
    </g>
    <g opacity="0.55">
        <rect x="95" y="669" width="440" height="104" rx="10" fill="#ecfdf5" stroke="#059669" stroke-width="1.5" />
    </g>
    <rect x="90" y="664" width="440" height="104" rx="10" fill="#ecfdf5" filter="url(#fs)" />
    <rect x="90" y="664" width="440" height="104" rx="10" fill="none" stroke="#059669" stroke-width="2" />
    <text x="310" y="690" text-anchor="middle" fill="#111110" font-size="14" font-weight="700">Run Tests in Containers</text>
    <text x="310" y="710" text-anchor="middle" fill="#6b6a65" font-size="12">Install pytest, mount repo, execute tests</text>
    <text x="310" y="728" text-anchor="middle" fill="#6b6a65" font-size="12">Output: report_thread_N.xml (per container)</text>
    <text x="310" y="750" text-anchor="middle" fill="#059669" font-size="11" font-weight="600">⚡ up to 6 in parallel</text>

    <line x1="310" y1="768" x2="310" y2="788" stroke="#b0afa9" stroke-width="1.5" marker-end="url(#a)" />

    <!-- SYNC CHECKPOINT -->
    <rect x="162" y="792" width="296" height="40" rx="8" fill="white" stroke="#e2e1db"
        stroke-width="1.2" stroke-dasharray="5,3" />
    <text x="310" y="812" dy="0.35em" text-anchor="middle" fill="#6b6a65" font-size="12" font-weight="500">Container tests complete ✓</text>

    <line x1="310" y1="832" x2="310" y2="851" stroke="#b0afa9" stroke-width="1.5" marker-end="url(#a)" />

    <!-- CONVERGENCE DOT -->
    <circle cx="310" cy="861" r="7" fill="#b0afa9" opacity="0.45" />

    <line x1="310" y1="868" x2="310" y2="892" stroke="#b0afa9" stroke-width="1.5" marker-end="url(#a)" />

    <!-- RUN TESTS ON LOCALHOST -->
    <rect x="90" y="896" width="440" height="88" rx="10" fill="#eff6ff" filter="url(#fs)" />
    <rect x="90" y="896" width="440" height="88" rx="10" fill="none" stroke="#2563eb" stroke-width="2" />
    <text x="310" y="922" text-anchor="middle" fill="#111110" font-size="14" font-weight="700">Run Tests on Localhost</text>
    <text x="310" y="942" text-anchor="middle" fill="#6b6a65" font-size="12">Main thread, pytest.main()</text>
    <text x="310" y="960" text-anchor="middle" fill="#6b6a65" font-size="12">Output: report_thread_main.xml</text>

    <line x1="310" y1="984" x2="310" y2="1004" stroke="#b0afa9" stroke-width="1.5" marker-end="url(#a)" />

    <!-- MERGE JUNIT XML REPORTS -->
    <rect x="72" y="1008" width="476" height="90" rx="10" fill="white" stroke="#2563eb"
        stroke-width="1.5" filter="url(#fs)" />
    <text x="310" y="1036" text-anchor="middle" fill="#111110" font-size="14" font-weight="600">Merge JUnit XML Reports</text>
    <text x="310" y="1058" text-anchor="middle" fill="#6b6a65" font-size="12">Parse all report_thread_*.xml + report_thread_main.xml</text>
    <text x="310" y="1078" text-anchor="middle" fill="#6b6a65" font-size="12">Generate unified pytest-style CLI output</text>

    <line x1="310" y1="1098" x2="310" y2="1126" stroke="#b0afa9" stroke-width="1.5" marker-end="url(#a)" />

    <!-- END -->
    <rect x="185" y="1130" width="250" height="52" rx="26" fill="#6d28d9" filter="url(#fm)" />
    <text x="310" y="1156" dy="0.35em" text-anchor="middle" fill="white" font-size="15" font-weight="600"
        letter-spacing="-0.01em">Test Results</text>
</svg>

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
