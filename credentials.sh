#!/usr/bin/env bash
ACCOUNT=740186269845
REGION=ap-south-1
SECRET_NAME=${REGION}-ecr-registry
EMAIL=neil.haria@thinkanalytics.in

TOKEN=$(aws ecr --region=${REGION} get-authorization-token --output text --query authorizationData[].authorizationToken | base64 -d | cut -d: -f2)

#  Create or replace registry sec
kubectl delete secret --ignore-not-found ${SECRET_NAME}
kubectl create secret docker-registry ${SECRET_NAME} \
    --docker-server=https://${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com \
    --docker-username=AWS \
    --docker-password="${TOKEN}" \
    --docker-email="${EMAIL}"
