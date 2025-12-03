import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  
  // Production optimizations
  build: {
    outDir: 'dist',
    sourcemap: false, // Disable sourcemaps in production for security
    minify: 'terser',
    cssMinify: true,
    
    // Advanced Rollup options for production
    rollupOptions: {
      output: {
        // Manual chunks for better caching
        manualChunks: {
          // Vendor chunks
          'vendor-react': ['react', 'react-dom'],
          'vendor-router': ['react-router-dom'],
          'vendor-ui': [
            '@radix-ui/react-dialog',
            '@radix-ui/react-dropdown-menu',
            '@radix-ui/react-alert-dialog',
            '@radix-ui/react-avatar',
            '@radix-ui/react-checkbox',
            '@radix-ui/react-label',
            '@radix-ui/react-navigation-menu',
            '@radix-ui/react-progress',
            '@radix-ui/react-select',
            '@radix-ui/react-separator',
            '@radix-ui/react-slot',
            '@radix-ui/react-tabs'
          ],
          'vendor-forms': [
            'react-hook-form',
            '@hookform/resolvers',
            'zod'
          ],
          'vendor-utils': [
            'axios',
            'clsx',
            'class-variance-authority',
            'tailwind-merge',
            'lucide-react'
          ],
          'vendor-charts': ['recharts'],
          'vendor-file': ['react-dropzone'],
          'vendor-toast': ['sonner'],
          'vendor-theme': ['next-themes']
        },
        
        // Asset naming for better caching
        chunkFileNames: (chunkInfo) => {
          const facadeModuleId = chunkInfo.facadeModuleId
            ? chunkInfo.facadeModuleId.split('/').pop()?.split('.')[0]
            : 'chunk';
          return `js/${facadeModuleId}-[hash].js`;
        },
        entryFileNames: 'js/main-[hash].js',
        assetFileNames: (assetInfo) => {
          
          if (/\.(css)$/i.test(assetInfo.name || '')) {
            return 'css/[name]-[hash].[ext]';
          }
          
          if (/\.(png|jpe?g|svg|gif|tiff|bmp|ico)$/i.test(assetInfo.name || '')) {
            return 'images/[name]-[hash].[ext]';
          }
          
          if (/\.(woff2?|eot|ttf|otf)$/i.test(assetInfo.name || '')) {
            return 'fonts/[name]-[hash].[ext]';
          }
          
          return 'assets/[name]-[hash].[ext]';
        }
      }
    },
    
    // Terser options for better minification
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log in production
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.info', 'console.debug'],
        passes: 2
      },
      mangle: {
        safari10: true
      },
      format: {
        comments: false
      }
    },
    
    // Chunk size warnings
    chunkSizeWarningLimit: 1000,
    
    // Asset inlining threshold
    assetsInlineLimit: 4096,
    
    // CSS code splitting
    cssCodeSplit: true,
    
    // Build target for modern browsers
    target: ['es2020', 'chrome80', 'firefox78', 'safari14', 'edge79'],
    
    // Optimize dependencies
    optimizeDeps: {
      include: [
        'react',
        'react-dom',
        'react-router-dom',
        'axios',
        'zod'
      ]
    }
  },
  
  // Preview server configuration for production testing
  preview: {
    port: 3000,
    host: true,
    strictPort: true
  },
  
  // Environment variables
  define: {
    'process.env.NODE_ENV': JSON.stringify('production'),
    '__DEV__': false
  },
  
  // CSS preprocessing
  css: {
    postcss: './postcss.config.js',
    devSourcemap: false
  },
  
  // PWA and asset optimization
  assetsInclude: ['**/*.woff2', '**/*.woff'],
  
  // Performance optimizations
  esbuild: {
    drop: ['console', 'debugger'],
    legalComments: 'none'
  }
})