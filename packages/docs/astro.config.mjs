import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
  integrations: [
    starlight({
      title: 'xSwarm-boss',
      description: 'AI Orchestration Layer for Multi-Project Development',
      logo: {
        src: './src/assets/logo.svg',
      },
      social: {
        github: 'https://github.com/chadananda/xswarm-boss',
      },
      sidebar: [
        {
          label: 'Introduction',
          items: [
            { label: 'What is xSwarm?', link: '/introduction/' },
            { label: 'Why xSwarm?', link: '/introduction/why-xswarm/' },
            { label: 'Key Features', link: '/introduction/key-features/' },
          ],
        },
        {
          label: 'Getting Started',
          items: [
            { label: 'Installation', link: '/getting-started/' },
            { label: 'Quick Start', link: '/getting-started/quick-start/' },
            { label: 'First Commands', link: '/getting-started/first-commands/' },
          ],
        },
        {
          label: 'Core Concepts',
          items: [
            { label: 'Architecture', link: '/core-concepts/' },
            { label: 'Overlord & Vassals', link: '/core-concepts/overlord-vassals/' },
            { label: 'Memory System', link: '/core-concepts/memory-system/' },
            { label: 'Security Model', link: '/core-concepts/security/' },
          ],
        },
        {
          label: 'User Interface',
          items: [
            { label: 'CLI Commands', link: '/user-interface/cli/' },
            { label: 'Voice Interface', link: '/user-interface/voice/' },
            { label: 'Dashboard (TUI)', link: '/user-interface/dashboard/' },
          ],
        },
        {
          label: 'Personality Themes',
          items: [
            { label: 'Overview', link: '/themes/' },
            { label: 'HAL 9000', link: '/themes/hal-9000/' },
            { label: 'Sauron', link: '/themes/sauron/' },
            { label: 'Creating Themes', link: '/themes/creating/' },
          ],
        },
        {
          label: 'Reference',
          items: [
            { label: 'Configuration', link: '/reference/configuration/' },
            { label: 'Troubleshooting', link: '/reference/troubleshooting/' },
            { label: 'FAQ', link: '/reference/faq/' },
          ],
        },
      ],
      customCss: [
        './src/styles/custom.css',
      ],
    }),
  ],
});
