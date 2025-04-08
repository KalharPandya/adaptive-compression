#!/bin/bash

# This script adds modimansi as a maintainer to the repository

curl -X PUT \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer YOUR_PERSONAL_ACCESS_TOKEN" \
  https://api.github.com/repos/KalharPandya/adaptive-compression/collaborators/modimansi \
  -d '{"permission":"maintain"}'

# Note: Replace YOUR_PERSONAL_ACCESS_TOKEN with your GitHub personal access token
# with repo permissions
