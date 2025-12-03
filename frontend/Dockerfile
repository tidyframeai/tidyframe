# Development stage
FROM node:20-alpine as development

WORKDIR /app

# Install dependencies only when needed
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host"]

# Build stage - outputs built files to /app/dist
FROM node:20-alpine as builder

WORKDIR /app

# Install all dependencies (including devDependencies for build)
COPY package*.json ./
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# The dist folder will be mounted as a volume
# No production nginx stage needed - main nginx will serve the files