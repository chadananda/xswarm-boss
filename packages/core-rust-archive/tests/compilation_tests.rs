// Compilation Tests
//
// These tests verify that the xswarm binary compiles and basic functionality works
// after fixing the wake word detector and threading issues.

#[cfg(test)]
mod tests {
    use std::process::Command;

    #[test]
    fn test_xswarm_binary_compiles() {
        // Test that the binary compiles successfully
        let output = Command::new("cargo")
            .args(&["build", "--bin", "xswarm"])
            .output()
            .expect("Failed to execute cargo build");

        assert!(
            output.status.success(),
            "xswarm binary should compile successfully. stderr: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    #[test]
    fn test_xswarm_help_command() {
        // Test that --help works
        let output = Command::new("cargo")
            .args(&["run", "--bin", "xswarm", "--", "--help"])
            .output()
            .expect("Failed to execute cargo run");

        assert!(
            output.status.success(),
            "xswarm --help should execute successfully"
        );

        // Cargo run outputs to both stdout and stderr, check both
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);
        let combined = format!("{}{}", stdout, stderr);

        assert!(
            combined.contains("Voice-First AI Assistant") || combined.contains("voice-first"),
            "Help text should contain description. Output: {}",
            combined
        );
        assert!(
            combined.contains("Usage:"),
            "Help text should contain usage information"
        );
    }

    #[test]
    fn test_library_compiles() {
        // Test that the library compiles successfully
        let output = Command::new("cargo")
            .args(&["build", "--lib"])
            .output()
            .expect("Failed to execute cargo build");

        assert!(
            output.status.success(),
            "xswarm library should compile successfully. stderr: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    #[test]
    fn test_library_tests_compile() {
        // Test that the library tests compile
        let output = Command::new("cargo")
            .args(&["test", "--lib", "--no-run"])
            .output()
            .expect("Failed to execute cargo test");

        assert!(
            output.status.success(),
            "Library tests should compile successfully. stderr: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }
}
