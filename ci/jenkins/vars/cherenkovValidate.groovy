def call(Map config) {
    // Default values
    def targetUrl = config.targetUrl ?: ''
    def specPath = config.specPath ?: ''
    def format = config.format ?: 'junit'
    def failOnDrift = config.failOnDrift != null ? config.failOnDrift : true
    def exportJira = config.exportJira ?: false

    if (!targetUrl || !specPath) {
        error("cherenkovValidate requires 'targetUrl' and 'specPath'")
    }

    echo "Running CHERENKOV Validation..."
    echo "Target: ${targetUrl}"
    echo "Spec: ${specPath}"

    // Build the command
    def cmd = "cherenkov validate --target ${targetUrl} --spec ${specPath} --format ${format} --quiet"
    
    if (failOnDrift) {
        cmd += " --fail-on-drift"
    }
    
    if (exportJira) {
        cmd += " --export-jira"
    }

    // Execute in a docker container or assuming cherenkov is installed on the agent
    sh "python3 -m pip install cherenkov-qa"
    
    try {
        sh "${cmd}"
    } catch (Exception e) {
        if (failOnDrift) {
            error("CHERENKOV Conformance check failed: ${e.message}")
        } else {
            echo "CHERENKOV Validation found drift, but failOnDrift is false."
            currentBuild.result = 'UNSTABLE'
        }
    }
}
