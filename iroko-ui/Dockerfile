FROM docker.uclv.cu/nginx:alpine

# Copy built Angular app
COPY dist/iroko-ui/browser /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]