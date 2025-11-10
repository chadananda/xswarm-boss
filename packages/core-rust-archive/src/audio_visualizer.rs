// Audio Visualizer Module - ASCII Art Audio Visualization
//
// Provides animated ASCII art visualization for voice activity and audio output.
// Features different animation states for various audio conditions:
// - Idle: System ready but silent
// - Listening: Microphone active, waiting for speech
// - Speaking: User is speaking (varying intensity)
// - Processing: AI is thinking/generating response
// - Output: AI is speaking back

use std::time::{Duration, Instant};

/// Audio activity level
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum AudioLevel {
    Silent,      // No audio detected
    Quiet,       // Low audio level
    Normal,      // Normal speaking level
    Loud,        // Loud audio level
}

impl AudioLevel {
    /// Determine audio level from RMS (Root Mean Square) amplitude
    ///
    /// # Arguments
    /// * `rms` - RMS amplitude in range [0.0, 1.0]
    ///
    /// # Returns
    /// Corresponding audio level
    pub fn from_rms(rms: f32) -> Self {
        if rms < 0.01 {
            AudioLevel::Silent
        } else if rms < 0.1 {
            AudioLevel::Quiet
        } else if rms < 0.5 {
            AudioLevel::Normal
        } else {
            AudioLevel::Loud
        }
    }

    /// Calculate RMS from audio samples
    ///
    /// # Arguments
    /// * `samples` - Audio samples in range [-1.0, 1.0]
    ///
    /// # Returns
    /// RMS amplitude
    pub fn calculate_rms(samples: &[f32]) -> f32 {
        if samples.is_empty() {
            return 0.0;
        }

        let sum: f32 = samples.iter().map(|&s| s * s).sum();
        (sum / samples.len() as f32).sqrt()
    }
}

/// Audio visualizer state
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum VisualizerState {
    Idle,           // System ready, no activity
    Listening,      // Microphone active
    Speaking,       // User speaking
    Processing,     // AI processing/thinking
    AiSpeaking,     // AI generating speech
}

/// Animation frame for visualizer
#[derive(Debug, Clone)]
pub struct AnimationFrame {
    /// ASCII art lines for this frame
    pub lines: Vec<String>,
    /// Duration to display this frame
    pub duration: Duration,
}

/// Audio visualizer with animation
pub struct AudioVisualizer {
    /// Current visualizer state
    pub state: VisualizerState,
    /// Current audio level
    audio_level: AudioLevel,
    /// Current animation frame index
    frame_index: usize,
    /// Time when current frame started
    frame_start: Instant,
    /// Width of visualizer display
    width: usize,
    /// Height of visualizer display
    height: usize,
}

impl AudioVisualizer {
    /// Create a new audio visualizer
    ///
    /// # Arguments
    /// * `width` - Width in characters
    /// * `height` - Height in lines
    pub fn new(width: usize, height: usize) -> Self {
        Self {
            state: VisualizerState::Idle,
            audio_level: AudioLevel::Silent,
            frame_index: 0,
            frame_start: Instant::now(),
            width,
            height,
        }
    }

    /// Update visualizer state
    pub fn set_state(&mut self, state: VisualizerState) {
        if self.state != state {
            self.state = state;
            self.frame_index = 0;
            self.frame_start = Instant::now();
        }
    }

    /// Update audio level (for speaking/listening states)
    pub fn set_audio_level(&mut self, level: AudioLevel) {
        self.audio_level = level;
    }

    /// Update from audio samples
    pub fn update_from_samples(&mut self, samples: &[f32]) {
        let rms = AudioLevel::calculate_rms(samples);
        self.audio_level = AudioLevel::from_rms(rms);
    }

    /// Update from raw RMS amplitude value
    /// This is useful when receiving pre-calculated RMS from audio processing
    pub fn update_from_rms(&mut self, rms: f32) {
        self.audio_level = AudioLevel::from_rms(rms);
    }

    /// Get current animation frame
    pub fn get_frame(&mut self) -> Vec<String> {
        let frames = self.get_animation_frames();

        // Check if we need to advance to next frame
        if !frames.is_empty() {
            let current_frame = &frames[self.frame_index % frames.len()];

            if self.frame_start.elapsed() >= current_frame.duration {
                self.frame_index = (self.frame_index + 1) % frames.len();
                self.frame_start = Instant::now();
            }
        }

        // Get the current frame
        if frames.is_empty() {
            self.get_idle_frames()[0].lines.clone()
        } else {
            frames[self.frame_index % frames.len()].lines.clone()
        }
    }

    /// Get animation frames based on current state
    fn get_animation_frames(&self) -> Vec<AnimationFrame> {
        match self.state {
            VisualizerState::Idle => self.get_idle_frames(),
            VisualizerState::Listening => self.get_listening_frames(),
            VisualizerState::Speaking => self.get_speaking_frames(),
            VisualizerState::Processing => self.get_processing_frames(),
            VisualizerState::AiSpeaking => self.get_ai_speaking_frames(),
        }
    }

    /// Idle state frames - gentle pulsing
    fn get_idle_frames(&self) -> Vec<AnimationFrame> {
        vec![
            AnimationFrame {
                lines: vec![
                    "                    ".to_string(),
                    "       ♪   ♫        ".to_string(),
                    "     ━━━━━━━━       ".to_string(),
                    "      Ready         ".to_string(),
                ],
                duration: Duration::from_millis(500),
            },
            AnimationFrame {
                lines: vec![
                    "                    ".to_string(),
                    "       ♫   ♪        ".to_string(),
                    "     ━━━━━━━━       ".to_string(),
                    "      Ready         ".to_string(),
                ],
                duration: Duration::from_millis(500),
            },
        ]
    }

    /// Listening state frames - animated microphone
    fn get_listening_frames(&self) -> Vec<AnimationFrame> {
        vec![
            AnimationFrame {
                lines: vec![
                    "                    ".to_string(),
                    "         🎤         ".to_string(),
                    "       ▁ ▁ ▁        ".to_string(),
                    "     Listening      ".to_string(),
                ],
                duration: Duration::from_millis(200),
            },
            AnimationFrame {
                lines: vec![
                    "                    ".to_string(),
                    "         🎤         ".to_string(),
                    "       ▃ ▃ ▃        ".to_string(),
                    "     Listening      ".to_string(),
                ],
                duration: Duration::from_millis(200),
            },
            AnimationFrame {
                lines: vec![
                    "                    ".to_string(),
                    "         🎤         ".to_string(),
                    "       ▅ ▅ ▅        ".to_string(),
                    "     Listening      ".to_string(),
                ],
                duration: Duration::from_millis(200),
            },
            AnimationFrame {
                lines: vec![
                    "                    ".to_string(),
                    "         🎤         ".to_string(),
                    "       ▃ ▃ ▃        ".to_string(),
                    "     Listening      ".to_string(),
                ],
                duration: Duration::from_millis(200),
            },
        ]
    }

    /// Speaking state frames - intensity based on audio level
    fn get_speaking_frames(&self) -> Vec<AnimationFrame> {
        match self.audio_level {
            AudioLevel::Silent => vec![
                AnimationFrame {
                    lines: vec![
                        "                    ".to_string(),
                        "         🎤         ".to_string(),
                        "       ━━━━━        ".to_string(),
                        "      Silent        ".to_string(),
                    ],
                    duration: Duration::from_millis(300),
                },
            ],
            AudioLevel::Quiet => vec![
                AnimationFrame {
                    lines: vec![
                        "                    ".to_string(),
                        "     ♪   🎤   ♫     ".to_string(),
                        "       ≋ ≋ ≋        ".to_string(),
                        "      Speaking      ".to_string(),
                    ],
                    duration: Duration::from_millis(150),
                },
                AnimationFrame {
                    lines: vec![
                        "                    ".to_string(),
                        "     ♫   🎤   ♪     ".to_string(),
                        "       ∼ ∼ ∼        ".to_string(),
                        "      Speaking      ".to_string(),
                    ],
                    duration: Duration::from_millis(150),
                },
            ],
            AudioLevel::Normal => vec![
                AnimationFrame {
                    lines: vec![
                        "                    ".to_string(),
                        "   ♪ ♫   🎤   ♪ ♫   ".to_string(),
                        "      ≋≋≋≋≋≋        ".to_string(),
                        "      Speaking      ".to_string(),
                    ],
                    duration: Duration::from_millis(100),
                },
                AnimationFrame {
                    lines: vec![
                        "                    ".to_string(),
                        "   ♫ ♪   🎤   ♫ ♪   ".to_string(),
                        "      ∼∼∼∼∼∼        ".to_string(),
                        "      Speaking      ".to_string(),
                    ],
                    duration: Duration::from_millis(100),
                },
                AnimationFrame {
                    lines: vec![
                        "                    ".to_string(),
                        "   ♪ ♫   🎤   ♪ ♫   ".to_string(),
                        "      ≈≈≈≈≈≈        ".to_string(),
                        "      Speaking      ".to_string(),
                    ],
                    duration: Duration::from_millis(100),
                },
            ],
            AudioLevel::Loud => vec![
                AnimationFrame {
                    lines: vec![
                        "  ♪ ♫ ♪ ♫ ♪ ♫ ♪ ♫  ".to_string(),
                        "   ♪ ♫   🎤   ♪ ♫   ".to_string(),
                        "     ≈≈≈≈≈≈≈≈≈      ".to_string(),
                        "    SPEAKING!!      ".to_string(),
                    ],
                    duration: Duration::from_millis(80),
                },
                AnimationFrame {
                    lines: vec![
                        "  ♫ ♪ ♫ ♪ ♫ ♪ ♫ ♪  ".to_string(),
                        "   ♫ ♪   🎤   ♫ ♪   ".to_string(),
                        "     ≋≋≋≋≋≋≋≋≋      ".to_string(),
                        "    SPEAKING!!      ".to_string(),
                    ],
                    duration: Duration::from_millis(80),
                },
                AnimationFrame {
                    lines: vec![
                        "  ♪ ♫ ♪ ♫ ♪ ♫ ♪ ♫  ".to_string(),
                        "   ♪ ♫   🎤   ♪ ♫   ".to_string(),
                        "     ∼∼∼∼∼∼∼∼∼      ".to_string(),
                        "    SPEAKING!!      ".to_string(),
                    ],
                    duration: Duration::from_millis(80),
                },
            ],
        }
    }

    /// Processing state frames - thinking animation
    fn get_processing_frames(&self) -> Vec<AnimationFrame> {
        vec![
            AnimationFrame {
                lines: vec![
                    "                    ".to_string(),
                    "         🤔         ".to_string(),
                    "       ●  ○  ○      ".to_string(),
                    "     Processing     ".to_string(),
                ],
                duration: Duration::from_millis(200),
            },
            AnimationFrame {
                lines: vec![
                    "                    ".to_string(),
                    "         🤔         ".to_string(),
                    "       ○  ●  ○      ".to_string(),
                    "     Processing     ".to_string(),
                ],
                duration: Duration::from_millis(200),
            },
            AnimationFrame {
                lines: vec![
                    "                    ".to_string(),
                    "         🤔         ".to_string(),
                    "       ○  ○  ●      ".to_string(),
                    "     Processing     ".to_string(),
                ],
                duration: Duration::from_millis(200),
            },
            AnimationFrame {
                lines: vec![
                    "                    ".to_string(),
                    "         🤔         ".to_string(),
                    "       ○  ●  ○      ".to_string(),
                    "     Processing     ".to_string(),
                ],
                duration: Duration::from_millis(200),
            },
        ]
    }

    /// AI speaking state frames - TRON-style amplitude visualization
    fn get_ai_speaking_frames(&self) -> Vec<AnimationFrame> {
        // TRON-style amplitude bars that react to audio level
        let bars = self.generate_tron_amplitude_bars(self.audio_level);

        vec![
            AnimationFrame {
                lines: vec![
                    "┌─ AI OUTPUT ──────┐".to_string(),
                    format!("│ {} │", bars),
                    "│   MOSHI          │".to_string(),
                    "└──────────────────┘".to_string(),
                ],
                duration: Duration::from_millis(50), // Fast refresh for real-time feel
            },
        ]
    }

    /// Generate microphone input visualization frames
    /// Similar to AI speaking but with different styling to distinguish input from output
    pub fn get_mic_input_frames(&self) -> Vec<String> {
        // TRON-style amplitude bars for microphone input
        // Use different characters to visually distinguish from AI output
        let bars = self.generate_mic_amplitude_bars(self.audio_level);

        vec![
            "┌─ MIC INPUT ──────┐".to_string(),
            format!("│ {} │", bars),
            "│   Microphone     │".to_string(),
            "└──────────────────┘".to_string(),
        ]
    }

    /// Generate microphone input amplitude bars (different style from AI output)
    /// Returns a string of amplitude bars using different characters: ▂▃▄▅▆▇█
    fn generate_mic_amplitude_bars(&self, level: AudioLevel) -> String {
        // Different bar characters for microphone input (to distinguish from output)
        // These have a more "blocky" appearance
        const BAR_CHARS: [char; 8] = ['▂', '▃', '▄', '▅', '▆', '▇', '█', '█'];

        // Determine number of bars at each height based on audio level
        let (max_height, variation): (usize, usize) = match level {
            AudioLevel::Silent => (0, 0),
            AudioLevel::Quiet => (2, 1),
            AudioLevel::Normal => (5, 2),
            AudioLevel::Loud => (7, 3),
        };

        // Generate 16 bars with wave pattern (similar to AI output but different phase)
        let mut bars = String::with_capacity(16);
        let time_offset = (self.frame_index as f32 * 0.7) as usize; // Different speed for mic

        for i in 0..16 {
            // Create wave pattern that moves based on frame_index
            // Different phase to make it visually distinct from AI output
            let wave_pos = ((i + time_offset + 4) % 8) as f32 / 8.0 * std::f32::consts::PI * 2.0;
            let wave_value = (wave_pos.sin() * variation as f32).abs() as usize;

            // Calculate bar height with wave variation
            let height = if max_height > 0 {
                (max_height.saturating_sub(variation) + wave_value).min(7)
            } else {
                0
            };

            bars.push(BAR_CHARS[height]);
        }

        bars
    }

    /// Generate TRON-style amplitude bars based on audio level
    /// Returns a string of amplitude bars like: ▁▂▃▄▅▆▇█▇▆▅▄▃▂▁
    fn generate_tron_amplitude_bars(&self, level: AudioLevel) -> String {
        // Amplitude bar characters from low to high
        const BAR_CHARS: [char; 8] = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'];

        // Determine number of bars at each height based on audio level
        let (max_height, variation): (usize, usize) = match level {
            AudioLevel::Silent => (0, 0),
            AudioLevel::Quiet => (2, 1),
            AudioLevel::Normal => (5, 2),
            AudioLevel::Loud => (7, 3),
        };

        // Generate 16 bars with wave pattern
        let mut bars = String::with_capacity(16);
        let time_offset = (self.frame_index as f32 * 0.5) as usize;

        for i in 0..16 {
            // Create wave pattern that moves based on frame_index
            let wave_pos = ((i + time_offset) % 8) as f32 / 8.0 * std::f32::consts::PI * 2.0;
            let wave_value = (wave_pos.sin() * variation as f32).abs() as usize;

            // Calculate bar height with wave variation
            let height = if max_height > 0 {
                (max_height.saturating_sub(variation) + wave_value).min(7)
            } else {
                0
            };

            bars.push(BAR_CHARS[height]);
        }

        bars
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_audio_level_from_rms() {
        assert_eq!(AudioLevel::from_rms(0.0), AudioLevel::Silent);
        assert_eq!(AudioLevel::from_rms(0.005), AudioLevel::Silent);
        assert_eq!(AudioLevel::from_rms(0.05), AudioLevel::Quiet);
        assert_eq!(AudioLevel::from_rms(0.3), AudioLevel::Normal);
        assert_eq!(AudioLevel::from_rms(0.8), AudioLevel::Loud);
    }

    #[test]
    fn test_calculate_rms() {
        // Test silence
        let silence = vec![0.0; 100];
        assert_eq!(AudioLevel::calculate_rms(&silence), 0.0);

        // Test constant signal
        let constant = vec![0.5; 100];
        assert!((AudioLevel::calculate_rms(&constant) - 0.5).abs() < 0.001);

        // Test empty
        assert_eq!(AudioLevel::calculate_rms(&[]), 0.0);
    }

    #[test]
    fn test_visualizer_state_changes() {
        let mut viz = AudioVisualizer::new(20, 4);

        // Start in idle
        assert_eq!(viz.state, VisualizerState::Idle);

        // Change to listening
        viz.set_state(VisualizerState::Listening);
        assert_eq!(viz.state, VisualizerState::Listening);
        assert_eq!(viz.frame_index, 0);

        // Change to speaking
        viz.set_state(VisualizerState::Speaking);
        assert_eq!(viz.state, VisualizerState::Speaking);
    }

    #[test]
    fn test_visualizer_frames() {
        let mut viz = AudioVisualizer::new(20, 4);

        // Get idle frame
        let frame = viz.get_frame();
        assert_eq!(frame.len(), 4);

        // Set to listening
        viz.set_state(VisualizerState::Listening);
        let frame = viz.get_frame();
        assert_eq!(frame.len(), 4);
    }
}
