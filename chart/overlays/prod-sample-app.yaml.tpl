apiVersion: helm.toolkit.fluxcd.io/v2beta1
kind: HelmRelease
metadata:
  name: sample-app
  namespace: default
spec:
  chart:
    spec:
      version: ${CHART_VERSION}
