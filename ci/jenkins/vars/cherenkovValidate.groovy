def call(Map config) {
    // Default values
    def targetUrl = config.targetUrl ?: ''
    def specPath = config.specPath ?: ''
    def format = config.format ?: 'junit'
    def failOnDrift = config.failOnDrift != null ? config.failOnDrift : true

    if (!targetUrl || !specPath) {
        error("cherenkovValidate requires 'targetUrl' and 'specPath'")
    }

    // Jira export is not a `validate` flag. It is exposed as the
    // `export_jira_ticket` MCP tool — see cherenkov/mcp/handlers.py. Passing an
    // --export-jira option here previously produced a CLI usage error that this
    // library then reported as a failed conformance check.
    if (config.exportJira) {
        echo "cherenkovValidate: 'exportJira' is not supported by the CLI; " +
             "use the export_jira_ticket MCP tool instead. Ignoring."
    }

    echo "Running CHERENKOV Validation..."
    echo "Target: ${targetUrl}"
    echo "Spec: ${specPath}"

    def cmd = "cherenkov validate --target ${targetUrl} --spec ${specPath} --format ${format} --quiet"

    if (failOnDrift) {
        cmd += " --fail-on-drift"
    }

    // Execute in a docker container or assuming cherenkov is installed on the agent
    sh "python3 -m pip install cherenkov-qa"

    // returnStatus (rather than try/catch) so a usage error can be told apart
    // from a real conformance failure. Click exits 2 when it rejects the
    // invocation itself; reporting that as drift would tell the user their API
    // diverged when CHERENKOV never ran.
    def status = sh(script: cmd, returnStatus: true)

    if (status == 0) {
        echo "CHERENKOV Validation passed."
    } else if (status == 2) {
        error("CHERENKOV could not run: the CLI rejected the command (exit 2). " +
              "This is a usage/configuration error, not a conformance failure.")
    } else if (failOnDrift) {
        error("CHERENKOV Conformance check failed (exit ${status}).")
    } else {
        echo "CHERENKOV Validation found drift, but failOnDrift is false."
        currentBuild.result = 'UNSTABLE'
    }
}
