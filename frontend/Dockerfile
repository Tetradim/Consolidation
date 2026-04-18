# ============================================================
# Trading Bot Frontend Dockerfile
# React Native / Expo web build
# ============================================================

# --------------------------------------------------------
# Stage 1: Build dependencies
# --------------------------------------------------------
FROM node:20-alpine AS builder

# Install dependencies
WORKDIR /app

# Copy package files
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies
RUN npm ci --legacy-peer-deps

# Copy source code
COPY frontend/ ./

# Build the web app
ENV NODE_ENV=production
RUN npx expo export:web --platform web

# --------------------------------------------------------
# Stage 2: Production nginx
# --------------------------------------------------------
FROM nginx:alpine AS production

# Copy built assets
COPY --from=builder /app/web-build /usr/share/nginx/html

# Copy nginx config
COPY frontend/nginx.conf /etc/nginx/nginx.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]