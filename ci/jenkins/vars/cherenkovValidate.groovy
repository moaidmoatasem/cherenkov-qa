def call(Map config) {
    // Default values
    def targetUrl = config.targetUrl ?: ''
    def specPath = config.specPath ?: ''
    def format = config.format ?: 'junit'
    def failOnDrift = config.failOnDrift != null ? config.failOnDrift : true

    if (!targetUrl || !specPath) {
        error("cherenkovValidate requires 'targetUrl' and 'specPath'")
    }

    // `exportJira` used to append `--export-jira`, an option that exists on no
    // CHERENKOV command. Setting it always failed the build, and the catch
    // below reported that usage error as a conformance finding — so a pipeline
    // misconfiguration looked like the API under test was broken. Jira export
    // is available through the MCP tool `export_jira_ticket`, not the CLI.
    if (config.exportJira) {
        error("cherenkovValidate: 'exportJira' is not supported. The CLI has no " +
              "Jira export flag; use the MCP tool 'export_jira_ticket' instead.")
    }

    echo "Running CHERENKOV Validation..."
    echo "Target: ${targetUrl}"
    echo "Spec: ${specPath}"

    // Build the command
    def cmd = "cherenkov validate --target ${targetUrl} --spec ${specPath} --format ${format} --quiet"

    if (failOnDrift) {
        cmd += " --fail-on-drift"
    }

    // Execute in a docker container or assuming cherenkov is installed on the agent
    sh "python3 -m pip install cherenkov-qa"

    // returnStatus rather than try/catch: it lets a usage error (Click exits 2)
    // be reported as what it is instead of being relabelled a conformance
    // failure, which is what made the --export-jira breakage so misleading.
    def status = sh(script: cmd, returnStatus: true)

    if (status == 0) {
        echo "CHERENKOV Validation passed."
    } else if (status == 2) {
        error("CHERENKOV could not run: the command was rejected as invalid usage " +
              "(exit 2). This is a pipeline configuration problem, not a " +
              "conformance finding. Command: ${cmd}")
    } else if (failOnDrift) {
        error("CHERENKOV Conformance check failed (exit ${status}).")
    } else {
        echo "CHERENKOV Validation found drift, but failOnDrift is false."
        currentBuild.result = 'UNSTABLE'
    }
}
