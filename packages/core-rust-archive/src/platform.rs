use std::env;

/// Detected operating system
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Platform {
    MacOS,
    Linux,
    Windows,
    Unknown,
}

/// Detected CPU architecture
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Architecture {
    X86_64,
    Aarch64,
    Unknown,
}

impl Platform {
    /// Detect the current platform
    pub fn current() -> Self {
        if cfg!(target_os = "macos") {
            Platform::MacOS
        } else if cfg!(target_os = "linux") {
            Platform::Linux
        } else if cfg!(target_os = "windows") {
            Platform::Windows
        } else {
            Platform::Unknown
        }
    }

    /// Get platform name as string
    pub fn as_str(&self) -> &'static str {
        match self {
            Platform::MacOS => "macOS",
            Platform::Linux => "Linux",
            Platform::Windows => "Windows",
            Platform::Unknown => "Unknown",
        }
    }

    /// Check if voice features are fully supported on this platform
    pub fn supports_voice(&self) -> bool {
        match self {
            Platform::MacOS | Platform::Linux => true,
            Platform::Windows => false, // Needs testing
            Platform::Unknown => false,
        }
    }

    /// Check if systemd integration is available
    pub fn supports_systemd(&self) -> bool {
        matches!(self, Platform::Linux)
    }

    /// Get the default config directory for this platform
    pub fn config_dir_name(&self) -> &'static str {
        match self {
            Platform::MacOS => "Library/Application Support/xswarm",
            Platform::Linux | Platform::Windows => ".config/xswarm",
            Platform::Unknown => ".config/xswarm",
        }
    }
}

impl Architecture {
    /// Detect the current CPU architecture
    pub fn current() -> Self {
        if cfg!(target_arch = "x86_64") {
            Architecture::X86_64
        } else if cfg!(target_arch = "aarch64") {
            Architecture::Aarch64
        } else {
            Architecture::Unknown
        }
    }

    /// Get architecture name as string
    pub fn as_str(&self) -> &'static str {
        match self {
            Architecture::X86_64 => "x86_64",
            Architecture::Aarch64 => "aarch64",
            Architecture::Unknown => "unknown",
        }
    }
}

/// Get comprehensive platform information
pub struct PlatformInfo {
    pub platform: Platform,
    pub arch: Architecture,
    pub is_dev_mode: bool,
}

impl PlatformInfo {
    /// Detect current platform information
    pub fn detect() -> Self {
        Self {
            platform: Platform::current(),
            arch: Architecture::current(),
            is_dev_mode: cfg!(debug_assertions),
        }
    }

    /// Display platform information
    pub fn display(&self) -> String {
        format!(
            "{} {} ({})",
            self.platform.as_str(),
            self.arch.as_str(),
            if self.is_dev_mode { "dev" } else { "release" }
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_platform_detection() {
        let platform = Platform::current();
        assert_ne!(platform, Platform::Unknown);
    }

    #[test]
    fn test_arch_detection() {
        let arch = Architecture::current();
        assert_ne!(arch, Architecture::Unknown);
    }

    #[test]
    fn test_platform_info() {
        let info = PlatformInfo::detect();
        assert!(!info.display().is_empty());
    }
}
