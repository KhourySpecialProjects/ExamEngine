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

# Now wait a bit more for S3 to initialize
echo "Giving S3 service time to initialize..."
sleep 10

# Try to create bucket (will succeed if bucket doesn't exist, or error if it does - both are ok)
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
