#!/bin/sh
set -e

echo "Waiting for LocalStack to be ready..."

# First, wait for LocalStack to respond at all
MAX_ATTEMPTS=60
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -sf http://localstack:4566/_localstack/health >/dev/null 2>&1; then
        echo "✓ LocalStack is responding!"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    if [ $((ATTEMPT % 5)) -eq 0 ]; then
        echo "Still waiting for LocalStack... (attempt $ATTEMPT/$MAX_ATTEMPTS)"
    fi
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "LocalStack not responding"
    exit 1
fi

# Wait for S3 service to be actually usable
echo "Waiting for S3 service to be ready..."
S3_READY=false
for i in $(seq 1 30); do
    if aws --endpoint-url=http://localstack:4566 s3 ls >/dev/null 2>&1; then
        echo "S3 service is ready!"
        S3_READY=true
        break
    fi
    echo "S3 not ready yet, attempt $i/30..."
    sleep 2
done

if [ "$S3_READY" = "false" ]; then
    echo "S3 service failed to become ready"
    exit 1
fi

# Try to create bucket
echo "Creating S3 bucket: exam-engine-csvs"
aws --endpoint-url=http://localstack:4566 \
    --region=us-east-1 \
    s3 mb s3://exam-engine-csvs 2>&1 | grep -v "BucketAlreadyOwnedByYou" || true

# Verify bucket exists
echo "📋 Verifying S3 bucket:"
if aws --endpoint-url=http://localstack:4566 s3 ls 2>/dev/null | grep -q exam-engine-csvs; then
    echo "Bucket 'exam-engine-csvs' exists"
else
    echo "Bucket not found in listing"
fi

echo ""
echo "LocalStack initialization complete!"
echo "S3 endpoint: http://localstack:4566"
echo "Bucket: exam-engine-csvs"
