# Project Root Detection Implementation

## Overview

The xswarm binary now automatically detects the project root directory and can be run from any location on the system. This allows the installed binary (`/usr/local/bin/xswarm`) to work correctly regardless of the user's current working directory.

## Changes Made

### 1. Enhanced `find_project_root()` Function

Located in `/packages/core/src/main.rs`, this function now implements a multi-strategy approach to locate the project root:

**Strategy 1: Environment Variable**
- Checks `XSWARM_PROJECT_DIR` environment variable first
- Allows users to explicitly set the project location

**Strategy 2: Walk Upward from Current Directory**
- Starts from `std::env::current_dir()`
- Walks up the directory tree (max 10 levels)
- Looks for `Cargo.toml` containing `name = "xswarm"`

**Strategy 3: Walk Upward from Executable Location**
- Gets the path of the running binary via `std::env::current_exe()`
- Walks up from the executable's directory
- Useful when binary is installed in system paths like `/usr/local/bin/`

**Strategy 4: Common Development Paths (Fallback)**
- Checks common development locations:
  - `~/Dropbox/Public/JS/Projects/xswarm-boss/packages/core`
  - `~/Projects/xswarm-boss/packages/core`
  - `~/projects/xswarm-boss/packages/core`
  - `~/code/xswarm-boss/packages/core`
  - `~/src/xswarm-boss/packages/core`
  - `~/dev/xswarm-boss/packages/core`

### 2. Helper Function for Root Detection

```rust
fn is_xswarm_root(path: &std::path::Path) -> bool {
    let cargo_path = path.join("Cargo.toml");
    if cargo_path.exists() {
        if let Ok(cargo_toml) = std::fs::read_to_string(&cargo_path) {
            return cargo_toml.contains("name = \"xswarm\"");
        }
    }
    false
}
```

This helper validates that a directory is actually the xswarm project root by checking for the presence of `Cargo.toml` with the correct package name.

### 3. Updated `run_dev_mode()` Function

The `--dev` flag now:
1. Uses `find_project_root()` to locate the project
2. Changes to that directory for building
3. Runs `cargo run` from the correct location

## Usage Examples

### From Any Directory

```bash
# Run from anywhere
cd /tmp
xswarm

# Development mode from anywhere
cd ~
xswarm --dev
```

### With Environment Variable

```bash
# Set project location explicitly
export XSWARM_PROJECT_DIR=/path/to/xswarm-boss/packages/core
xswarm --dev
```

### System-Wide Installation

```bash
# Install the binary
sudo cp target/release/xswarm /usr/local/bin/xswarm

# Run from anywhere
cd ~/Documents
xswarm

# Development mode still works
xswarm --dev
```

## Testing Results

✅ **Works from /tmp directory**
```bash
cd /tmp
xswarm --help  # Success
xswarm --dev   # Finds project root and builds
```

✅ **Works from home directory**
```bash
cd ~
xswarm --help  # Success
xswarm --dev   # Finds project root and builds
```

✅ **Works from project directory**
```bash
cd /path/to/xswarm-boss/packages/core
xswarm --dev   # Works as before
```

## Error Handling

If the project root cannot be found, the user receives a helpful error message:

```
Could not find xswarm project directory.
Tried:
- XSWARM_PROJECT_DIR environment variable
- Walking upward from current directory
- Walking upward from executable location
- Common development paths

Please set XSWARM_PROJECT_DIR environment variable to point to the packages/core directory.
```

## Implementation Details

### File Locations

- **Main implementation**: `/packages/core/src/main.rs`
  - `find_project_root()` function (lines 395-485)
  - `run_dev_mode()` function (uses find_project_root)

### Dependencies

No additional dependencies were required. The implementation uses only standard library functions:
- `std::env::current_dir()`
- `std::env::current_exe()`
- `std::env::var()`
- `std::path::PathBuf`
- `dirs::home_dir()`

### Performance

The project root detection is fast:
- Checks environment variable first (instant)
- Directory walking is limited to 10 levels (prevents infinite loops)
- Only performed once during startup

## Benefits

1. **User Convenience**: Binary can be installed system-wide and work from any directory
2. **Development Flexibility**: `--dev` flag works regardless of current directory
3. **CI/CD Ready**: Works in automated environments with environment variables
4. **Error Recovery**: Falls back to common paths if primary methods fail

## Future Enhancements

Potential improvements for the future:

1. **Cache the project root**: Store detected path in memory to avoid re-detection
2. **XDG Base Directory support**: Check `$XDG_DATA_HOME` for configurations
3. **Project configuration file**: Create `.xswarm-project` marker files
4. **Better error messages**: Show which strategies were tried and why they failed

## Compatibility

- ✅ macOS (tested)
- ✅ Linux (should work, uses standard paths)
- ⚠️  Windows (may need adjustments for path separators and common locations)

## Conclusion

The xswarm binary is now fully portable and can be run from any directory on the system. The `--dev` flag automatically locates the project root for rebuilding, making development workflows more convenient.
