FROM quay.io/lib/nginx:alpine

# Copy built Angular app
COPY dist/iroko-ui-pwa/browser /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]