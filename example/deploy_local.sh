
set -e

python3 ../helper/deploy.py server-test deploy_local

python3 ../helper/deploy.py server-test build upload_local




