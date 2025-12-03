FROM redis:7-alpine

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD redis-cli ping | grep PONG

# Set memory policy for production
CMD ["redis-server", "--maxmemory", "400mb", "--maxmemory-policy", "allkeys-lru", "--appendonly", "yes"]