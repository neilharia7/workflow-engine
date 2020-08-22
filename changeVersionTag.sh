#!/usr/bin/env bash

# cannot read & write to the file at the same time
# TODO figure out why the hell helm-chart doesn't work
sed "s/tagVersion/$1/g" helm-chart/values.yaml > temp.yaml
mv temp.yaml helm-chart/values.yaml

# Temp solution
sed "s/tagVersion/$1/g" k8s.yaml > temp.yaml
mv temp.yaml k8s.yaml
