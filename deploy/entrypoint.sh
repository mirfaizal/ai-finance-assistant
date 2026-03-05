#!/bin/sh
# This script injects runtime environment variables into the compiled React index.html
# It allows us to set VITE_AUTH0_* variables in the Hugging Face Space settings
# rather than baking them into the Docker image at build time.

# Find the index.html file
INDEX_FILE="/usr/share/nginx/html/index.html"

# If the file exists, perform the substitutions
if [ -f "$INDEX_FILE" ]; then
    # We replace a specific placeholder in the HTML head with our global window config
    
    # First, let's create the JS config string. We use safely escaped values.
    # If the env vars aren't set, they default to empty strings.
    CONFIG_JS="<script>window.ENV = { AUTH0_DOMAIN: \"${VITE_AUTH0_DOMAIN:-}\", AUTH0_CLIENT_ID: \"${VITE_AUTH0_CLIENT_ID:-}\", AUTH0_AUDIENCE: \"${VITE_AUTH0_AUDIENCE:-}\" };</script>"
    
    # We use sed to replace the <!-- INJECT_ENV --> placeholder with our config script
    sed -i "s|<!-- INJECT_ENV -->|$CONFIG_JS|g" "$INDEX_FILE"
    
    echo "Injected runtime configuration into $INDEX_FILE"
fi

# Finally, hand over control to supervisord as originally intended
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
