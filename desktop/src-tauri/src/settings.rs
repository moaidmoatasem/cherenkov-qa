use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct AppSettings {
    /// Base URL for the local Ollama instance, e.g. "http://localhost:11434".
    pub ollama_host: String,
    /// Request timeout in seconds for Ollama calls.
    pub ollama_timeout: u32,
    /// Network egress policy: "none" | "internal" | "any".
    pub egress_policy: String,
    /// Optional Redis connection URL (used when task queue is enabled).
    pub redis_url: Option<String>,
    /// VLM capability tier: "small" | "deep".
    pub vlm_tier: String,
    /// Absolute path to the project work directory.
    pub work_dir: String,
}

impl AppSettings {
    /// Load settings from a JSON file.  Returns `Default::default()` if the
    /// file does not exist or cannot be parsed.
    pub fn load(config_path: &std::path::Path) -> Self {
        let contents = match std::fs::read_to_string(config_path) {
            Ok(s) => s,
            Err(_) => return Self::default(),
        };
        serde_json::from_str(&contents).unwrap_or_default()
    }

    /// Persist settings to a JSON file, creating parent directories as needed.
    pub fn save(&self, config_path: &std::path::Path) -> Result<(), String> {
        if let Some(parent) = config_path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("Failed to create config directory: {}", e))?;
        }
        let json = serde_json::to_string_pretty(self)
            .map_err(|e| format!("Failed to serialize settings: {}", e))?;
        std::fs::write(config_path, json)
            .map_err(|e| format!("Failed to write settings file: {}", e))
    }

    /// Validate the settings, mirroring the rules enforced by the Python
    /// `Config.validate()` method.
    pub fn validate(&self) -> Result<(), String> {
        // ollama_host must be non-empty and look like a URL.
        if self.ollama_host.trim().is_empty() {
            return Err("ollama_host must not be empty.".into());
        }
        if !self.ollama_host.starts_with("http://") && !self.ollama_host.starts_with("https://") {
            return Err(
                "ollama_host must start with \"http://\" or \"https://\".".into(),
            );
        }

        // egress_policy must be one of the three allowed values.
        match self.egress_policy.as_str() {
            "none" | "internal" | "any" => {}
            other => {
                return Err(format!(
                    "egress_policy must be \"none\", \"internal\", or \"any\", got \"{}\".",
                    other
                ));
            }
        }

        // vlm_tier must be "small" or "deep".
        match self.vlm_tier.as_str() {
            "small" | "deep" => {}
            other => {
                return Err(format!(
                    "vlm_tier must be \"small\" or \"deep\", got \"{}\".",
                    other
                ));
            }
        }

        // work_dir must be a non-empty path.
        if self.work_dir.trim().is_empty() {
            return Err("work_dir must not be empty.".into());
        }

        // ollama_timeout must be positive.
        if self.ollama_timeout == 0 {
            return Err("ollama_timeout must be greater than 0.".into());
        }

        Ok(())
    }
}
