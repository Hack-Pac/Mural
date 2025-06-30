// Tailwind configuration
tailwind.config = {
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                // Custom theme colors
                light: {
                    bg: '#f8fafc',
                    surface: '#ffffff',
                    border: '#e2e8f0',
                    text: '#1e293b',
                    muted: '#64748b'
                },
                dark: {
                    bg: '#0f172a',
                    surface: '#1e293b',
                    border: '#334155',
                    text: '#f1f5f9',
                    muted: '#94a3b8'
                },
                coffee: {
                    bg: '#2d1b14',
                    surface: '#4a2c1a',
                    card: '#f5efe7',
                    border: '#6b3e26',
                    text: '#f4e4d1',
                    muted: '#d4b895',
                    accent: '#8b4513',
                    warm: '#cd853f'
                }
            }
        }
    }
};