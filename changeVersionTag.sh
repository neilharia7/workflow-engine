#!/usr/bin/env bash

# cannot read & write to the file at the same time
sed "s/tagVersion/$1/g" helm-chart/values.yaml > temp.yaml
mv temp.yaml helm-chart/values.yaml

sed "s/tagVersion/$1/g" helm-chart/Chart.yaml > temp.yaml
mv temp.yaml helm-chart/Chart.yaml

# Temp solution
sed "s/tagVersion/$1/g" k8s.yaml > temp.yaml
mv temp.yaml k8s.yaml
